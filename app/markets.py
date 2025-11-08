from flask import Blueprint, jsonify, request
from .db import SessionLocal, Market

bp = Blueprint("markets", __name__, url_prefix="/markets")


@bp.get("")
def list_markets():
    session = SessionLocal()
    try:
        items = session.query(Market).order_by(Market.id.desc()).limit(50).all()
        data = []
        for m in items:
            data.append({
                "id": m.id,
                "question": m.question,
                "status": m.status,
                "outcome_yes_price": m.outcome_yes_price,
                "outcome_no_price": m.outcome_no_price,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
        return jsonify(ok=True, markets=data)
    finally:
        session.close()


@bp.post("")
def create_market():
    # ВРЕМЕННО: без авторизации, без TON, для отладки API.
    payload = request.get_json(silent=True) or {}
    question = payload.get("question")

    if not question:
        return jsonify(ok=False, error="question_required"), 400

    session = SessionLocal()
    try:
        m = Market(
            question=question,
            description=payload.get("description"),
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        return jsonify(ok=True, id=m.id), 201
    finally:
        session.close()
