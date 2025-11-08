from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def root():
    return jsonify(status="ok", service="backend")


from .ton_routes import bp as ton_bp
app.register_blueprint(ton_bp)

from .telegram_auth import bp as tg_auth_bp
app.register_blueprint(tg_auth_bp)
