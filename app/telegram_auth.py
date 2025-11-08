import os
import hmac
import hashlib
import time
import json
import urllib.parse
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
import jwt

from app.db import SessionLocal, User

bp = Blueprint("telegram_auth", __name__, url_prefix="/auth")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")


def _validate_init_data(init_data: str, max_age: int = 600):
    """
    Валидация initData по официальным правилам Telegram WebApp.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """

    if not init_data or not BOT_TOKEN:
        return None

    # Разбор query-string в словарь
    parsed = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
    data = dict(parsed)

    their_hash = data.pop("hash", None)
    if not their_hash:
        return None

    # Контроль времени жизни auth_date
    auth_date_raw = data.get("auth_date")
    if auth_date_raw:
        try:
            auth_ts = int(auth_date_raw)
            if int(time.time()) - auth_ts > max_age:
                return None
        except ValueError:
            return None

    # Собираем строки key=value, сортируем по ключу
    data_check_arr = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_arr)

    # Ключ: HMAC_SHA256("WebAppData", BOT_TOKEN)
    secret_key = hmac.new(
        "WebAppData".encode(),
        BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()

    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, their_hash):
        return None

    # user — это JSON-строка
    user_raw = data.get("user")
    if not user_raw:
        return None

    try:
        user = json.loads(user_raw)
    except Exception:
        return None

    return user


@bp.post("/telegram")
def auth_telegram():
    """
    Вход:  { "init_data": "<Telegram.WebApp.initData>" }
    Выход при успехе:
    {
        "ok": true,
        "user": {...},
        "token": "<jwt>"
    }
    """
    body = request.get_json(silent=True) or {}
    init_data = body.get("init_data") or body.get("initData") or ""

    user = _validate_init_data(init_data)
    if not user:
        return jsonify({"ok": False, "error": "invalid_init_data"}), 401

    # --- upsert пользователя в БД ---
    session = SessionLocal()
    try:
        db_user = session.query(User).filter_by(telegram_id=user["id"]).first()
        if not db_user:
            db_user = User(telegram_id=user["id"])
            session.add(db_user)

        db_user.username = user.get("username")
        db_user.first_name = user.get("first_name")
        db_user.last_name = user.get("last_name")
        db_user.language_code = user.get("language_code")
        db_user.is_premium = str(user.get("is_premium"))

        db_user.updated_at = datetime.utcnow()
        if not db_user.created_at:
            db_user.created_at = datetime.utcnow()

        session.commit()
    except Exception:
        session.rollback()
        return jsonify({"ok": False, "error": "db_error"}), 500
    finally:
        session.close()

    # --- JWT для фронта ---
    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "user_id": user["id"],
            "exp": datetime.utcnow() + timedelta(days=7),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    return jsonify(
        {
            "ok": True,
            "user": {
                "id": user.get("id"),
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "language_code": user.get("language_code"),
                "is_premium": user.get("is_premium"),
            },
            "token": token,
        }
    )
