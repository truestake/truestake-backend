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
    if not init_data or not BOT_TOKEN:
        return None

    parsed = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
    data = dict(parsed)

    their_hash = data.pop("hash", None)
    if not their_hash:
        return None

    auth_date_raw = data.get("auth_date")
    if auth_date_raw:
        try:
            auth_ts = int(auth_date_raw)
            if int(time.time()) - auth_ts > max_age:
                return None
        except ValueError:
            return None

    data_check_arr = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_arr)

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
    body = request.get_json(silent=True) or {}
    init_data = body.get("init_data") or body.get("initData") or ""

    user = _validate_init_data(init_data)
    if not user:
        return jsonify({"ok": False, "error": "invalid_init_data"}), 401

    session = SessionLocal()
    try:
        db_user = session.query(User).filter_by(telegram_id=user["id"]).first()
        if not db_user:
            db_user = User(telegram_id=user["id"])
            session.add(db_user)

        db_user.username = user.get("username")
        session.commit()
    except Exception as e:
        session.rollback()
        print("[auth_telegram][db_error]", repr(e), flush=True)
        return jsonify({"ok": False, "error": "db_error"}), 500
    finally:
        session.close()

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
            },
            "token": token,
        }
    )


@bp.get("/me")
def me():
    """
    Проверка токена.
    Заголовок: Authorization: Bearer <jwt>
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"ok": False, "error": "no_token"}), 401

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return jsonify({"ok": False, "error": "invalid_token"}), 401

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        return jsonify({"ok": False, "error": "invalid_token"}), 401

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"ok": False, "error": "invalid_token"}), 401

    session = SessionLocal()
    try:
        db_user = session.query(User).filter_by(telegram_id=user_id).first()
    finally:
        session.close()

    if not db_user:
        return jsonify({"ok": False, "error": "user_not_found"}), 404

    return jsonify(
        {
            "ok": True,
            "user": {
                "id": db_user.telegram_id,
                "username": db_user.username,
            },
        }
    )
