import os
from datetime import datetime

from flask import Blueprint, request, jsonify
import jwt

from app.db import SessionLocal, Market, User

bp = Blueprint("markets", __name__, url_prefix="/markets")

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")


def _get_current_user():
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


@bp.get("")
def list_markets():
    """
    Лента событий для Mini App и бота.
    Фильтры:
      ?status=active|pending|...
      ?category=politics|sport|...
      ?search=текст
    """
    status = request.args.get("status", "active")
    category = request.args.get("category")
    search = request.args.get("search")

    db = SessionLocal()
    try:
        q = db.query(Market)

        if status:
            q = q.filter(Market.status == status)
        if category:
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
                    "prob_yes": m.probability_yes,
                    "volume_usd": m.volume_usd,
                    "resolution_ts": m.resolution_ts.isoformat()
                    if m.resolution_ts
                    else None,
                }
            )
    finally:
        db.close()

    return jsonify({"ok": True, "markets": items})


@bp.post("")
def create_market():
    """
    Создание события.
    Доступ: role=creator или role=admin.

    Вход JSON:
    {
      "question": "U.S. National Debt exceeds $40T by Dec 31, 2026",
      "category": "economy",
      "resolution_ts": "2026-12-31T23:59:59"
    }
    """
    user, err = _get_current_user()
    if err:
        return jsonify({"ok": False, "error": err}), 401

    if user.role not in ("creator", "admin"):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}

    question = (data.get("question") or "").strip()
    category = (data.get("category") or "").strip() or None
    resolution_ts_raw = (data.get("resolution_ts") or "").strip()

    if not question:
        return jsonify({"ok": False, "error": "question_required"}), 400

    resolution_ts = None
    if resolution_ts_raw:
        try:
            resolution_ts = datetime.fromisoformat(resolution_ts_raw)
        except Exception:
            return jsonify({"ok": False, "error": "bad_resolution_ts"}), 400

    status = "active" if user.role == "admin" else "pending"

    db = SessionLocal()
    try:
        m = Market(
            question=question,
            category=category,
            resolution_ts=resolution_ts,
            creator_telegram_id=user.telegram_id,
            status=status,
            probability_yes=50.0,
            volume_usd=0.0,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
    except Exception as e:
        db.rollback()
        print("[create_market][db_error]", repr(e), flush=True)
        return jsonify({"ok": False, "error": "db_error"}), 500
    finally:
        db.close()

    return jsonify(
        {
            "ok": True,
            "market": {
                "id": m.id,
                "status": m.status,
                "question": m.question,
            },
        }
    )


@bp.post("/activate/<int:market_id>")
def activate_market(market_id: int):
    """
    Апрув события.
    Доступ: role=admin.
    """
    user, err = _get_current_user()
    if err:
        return jsonify({"ok": False, "error": err}), 401

    if user.role != "admin":
        return jsonify({"ok": False, "error": "forbidden"}), 403

    db = SessionLocal()
    try:
        m = db.query(Market).filter_by(id=market_id).first()
        if not m:
            return jsonify({"ok": False, "error": "not_found"}), 404

        m.status = "active"
        m.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(m)
    except Exception as e:
        db.rollback()
        print("[activate_market][db_error]", repr(e), flush=True)
        return jsonify({"ok": False, "error": "db_error"}), 500
    finally:
        db.close()

    return jsonify({"ok": True, "market": {"id": m.id, "status": m.status}})
