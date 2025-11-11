import os
import time
import hmac
import hashlib
from urllib.parse import parse_qs

from flask import Blueprint, request, jsonify
import jwt

from .db import SessionLocal, User

bp = Blueprint("telegram_auth", __name__, url_prefix="/auth")

# Токен бота и секрет для подписи JWT
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
# TTL токена (по умолчанию 30 дней)
JWT_TTL = int(os.getenv("JWT_TTL", "2592000"))


# =========================
# Вспомогательные функции
# =========================

def _build_jwt(user: User) -> str:
    """
    Собираем JWT для Mini App.
    В payload кладём:
      - sub / user_id = telegram_id
    """
    now = int(time.time())
    payload = {
        "sub": str(user.telegram_id),
        "user_id": user.telegram_id,
        "exp": now + JWT_TTL,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    # В новых версиях jwt.encode возвращает str, в старых bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Проверка подписи initData от Telegram.

    Возвращает dict с данными пользователя, если всё ок,
    иначе None.
    """
    if not BOT_TOKEN:
        return None

    try:
        # initData приходит в виде query-string
        data = parse_qs(init_data, strict_parsing=True)
    except Exception:
        return None

    if "hash" not in data:
        return None

    tg_hash = data.pop("hash")[0]

    # Подготовка строки по правилам Telegram:
    # sort by key, join "key=value" через "\n"
    pairs = []
    for k in sorted(data.keys()):
        v = data[k][0]
        pairs.append(f"{k}={v}")
    check_string = "\n".join(pairs)

    secret_key = hashlib.sha256(BOT_TOKEN.encode("utf-8")).digest()
    hmac_hash = hmac.new(
        secret_key, check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if hmac_hash != tg_hash:
        return None

    # Извлекаем user из initData (поле "user" в JSON-строке)
    user_raw = data.get("user", [None])[0]
    if not user_raw:
        return None

    import json
    try:
        user = json.loads(user_raw)
    except Exception:
        return None

    return user


def _get_user_from_jwt(auth_header: str):
    """
    Достаём пользователя из заголовка Authorization: Bearer <token>.
    Возвращаем (user, error) — если error не None, значит ошибка.
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "no_token"

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None, "invalid_token"

    tg_id = payload.get("user_id") or payload.get("sub")
    if not tg_id:
        return None, "invalid_token"

    try:
        tg_id = int(tg_id)
    except ValueError:
        return None, "invalid_token"

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
    finally:
        db.close()

    if not user:
        return None, "user_not_found"

    return user, None


# =========================
# Эндпоинты
# =========================

@bp.post("/telegram")
def auth_telegram():
    """
    Основной эндпоинт авторизации из Telegram Mini App.

    Ожидает JSON:
      { "initData": "<строка initData из Telegram.WebApp.initData>" }

    1. Проверяем подпись initData.
    2. Создаём/обновляем пользователя в БД.
    3. Возвращаем JWT + user с ролью.
    """
    data = request.get_json(force=True) or {}
    init_data = data.get("initData") or ""
    user_data = _verify_telegram_init_data(init_data)
    if not user_data:
        return jsonify(ok=False, error="bad_init_data"), 400

    tg_id = user_data.get("id")
    username = user_data.get("username") or ""

    if not tg_id:
        return jsonify(ok=False, error="no_telegram_id"), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            # новый пользователь
            user = User(
                telegram_id=tg_id,
                username=username,
                role="user",  # по умолчанию обычный пользователь
            )
            db.add(user)
        else:
            # обновляем username если поменялся
            if username and user.username != username:
                user.username = username

        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        return jsonify(ok=False, error="db_error"), 500
    finally:
        db.close()

    token = _build_jwt(user)

    return jsonify(
        ok=True,
        token=token,
        user={
            "id": user.telegram_id,
            "username": user.username,
            "role": user.role or "user",
        },
    )


@bp.get("/me")
def auth_me():
    """
    Возвращает информацию о текущем пользователе по JWT.
    Используется фронтом, чтобы понять роль (guest/creator/admin).
    """
    auth = request.headers.get("Authorization", "")
    user, err = _get_user_from_jwt(auth)
    if err:
        # для фронта достаточно 401 + причина
        return jsonify(ok=False, error=err), 401

    return jsonify(
        ok=True,
        user={
            "id": user.telegram_id,
            "username": user.username,
            "role": user.role or "user",
        },
    )
