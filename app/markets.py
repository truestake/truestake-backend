import os
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
import jwt

from app.db import SessionLocal, Market, User

# Blueprint БЕЗ префикса, все пути указываем явно ниже
bp = Blueprint("markets", __name__)

# Секрет для проверки JWT (тот же, что в telegram_auth)
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")


def _get_current_user():
    """
    Достаём пользователя из заголовка Authorization: Bearer <token>.
    Возвращаем (user, error):
      - (User, None) если всё ок
      - (None, "error_key") если ошибка
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, "no_token"

    token = auth.split(" ", 1)[1].strip()
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


@bp.get("/markets")
def list_markets():
    """
    Лента рынков для Mini App и бота.

    Поддерживаемые query-параметры:
      ?status=active|pending|resolved|...
      ?category=politics|economy|crypto|...
      ?search=текст

    Возвращаем JSON:
      {
        "ok": true,
        "markets": [
          {
            "id": ...,
            "question": "...",
            "category": "...",
            "status": "active",
            "resolution_ts": "2026-12-31T23:59:59",
            "prob_yes": 62.5,
            "volume_usd": 348000.0,
            "logo_url": "...",
            "resolution_source": "..."
          },
          ...
        ]
      }
    """
    status = request.args.get("status") or None
    category = request.args.get("category") or None
    search = request.args.get("search") or None

    db = SessionLocal()
    try:
        q = db.query(Market)

        if status:
            q = q.filter(Market.status == status)

        if category and category != "all":
            q = q.filter(Market.category == category)

        if search:
            like = f"%{search}%"
            q = q.filter(Market.question.ilike(like))

        q = q.order_by(Market.created_at.desc()).limit(100)

        items = []
        for m in q.all():
            items.append(
                {
                    "id": m.id,
                    "question": m.question,
                    "category": m.category,
                    "status": m.status,
                    "resolution_ts": m.resolution_ts.isoformat()
                    if m.resolution_ts
                    else None,
                    "prob_yes": m.probability_yes,
                    "volume_usd": m.volume_usd,
                    "logo_url": getattr(m, "logo_url", None),
                    "resolution_source": getattr(m, "resolution_source", None),
                }
            )
    except Exception as e:
        current_app.logger.exception("[list_markets][error] %s", e)
        return jsonify(ok=False, error="db_error"), 500
    finally:
        db.close()

    return jsonify(ok=True, markets=items)


@bp.post("/markets")
def create_market():
    """
    Создание нового рынка.
    Доступно только для ролей: creator, admin.
    """
    user, err = _get_current_user()
    if err:
        return jsonify(ok=False, error=err), 401

    role = (user.role or "user").lower()
    if role not in ("creator", "admin"):
        return jsonify(ok=False, error="forbidden"), 403

    data = request.get_json(force=True) or {}

    question = (data.get("question") or "").strip()
    category = (data.get("category") or "other").strip()
    resolution_ts_str = (data.get("resolution_ts") or "").strip()
    logo_url = (data.get("logo_url") or "").strip() or None
    resolution_source = (data.get("resolution_source") or "").strip() or None

    if not question:
        return jsonify(ok=False, error="question_required"), 400

    resolution_ts = None
    if resolution_ts_str:
        try:
            resolution_ts = datetime.fromisoformat(resolution_ts_str)
        except ValueError:
            return jsonify(ok=False, error="bad_resolution_ts"), 400

    db = SessionLocal()
    try:
        m = Market(
            question=question,
            category=category,
            status="pending",
            resolution_ts=resolution_ts,
            creator_telegram_id=user.telegram_id,
            logo_url=logo_url,
            resolution_source=resolution_source,
        )
        db.add(m)
        db.commit()
        db.refresh(m)

        result = {
            "id": m.id,
            "status": m.status,
            "question": m.question,
            "category": m.category,
        }
        return jsonify(ok=True, market=result), 200
    except Exception as e:
        db.rollback()
        current_app.logger.exception("[create_market][db_error] %s", e)
        return jsonify(ok=False, error="db_error"), 500
    finally:
        db.close()


@bp.post("/markets/activate/<int:market_id>")
def activate_market(market_id: int):
    """
    Апрув/активация рынка.
    Доступ: только admin.
    """
    user, err = _get_current_user()
    if err:
        return jsonify(ok=False, error=err), 401

    if (user.role or "").lower() != "admin":
        return jsonify(ok=False, error="forbidden"), 403

    db = SessionLocal()
    try:
        m = db.query(Market).filter_by(id=market_id).first()
        if not m:
            return jsonify(ok=False, error="not_found"), 404

        m.status = "active"
        m.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(m)
    except Exception as e:
        db.rollback()
        current_app.logger.exception("[activate_market][db_error] %s", e)
        return jsonify(ok=False, error="db_error"), 500
    finally:
        db.close()

    return jsonify(ok=True, market={"id": m.id, "status": m.status})
