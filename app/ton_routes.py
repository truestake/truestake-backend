import os, requests
from flask import Blueprint, jsonify, request

bp = Blueprint("ton", __name__, url_prefix="/ton")
TONAPI_BASE = os.getenv("TONAPI_BASE", "https://testnet.tonapi.io")
TONAPI_KEY  = os.getenv("TONAPI_KEY", "")

def _h():
    return {"Authorization": f"Bearer {TONAPI_KEY}"} if TONAPI_KEY else {}

@bp.get("/wallet/<address>/balance")
def balance(address):
    r = requests.get(f"{TONAPI_BASE}/v2/accounts/{address}", headers=_h(), timeout=15)
    if r.status_code != 200:
        return jsonify({"ok": False, "status": r.status_code, "body": r.text}), 502
    data = r.json()
    bal = (data.get("balance") or data.get("ton",{}).get("balance") or 0)
    return jsonify({"ok": True, "address": address, "balance": int(bal)})

@bp.post("/transfer")
def transfer_mock():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify({"ok": True, "mode": "mock", "received": payload})
