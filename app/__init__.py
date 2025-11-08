from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Разрешаем запросы с фронта Mini App только к эндпоинту авторизации
CORS(
    app,
    resources={
        r"/auth/telegram": {
            "origins": ["https://app.corsarinc.ru"]
        }
    },
)


@app.get("/")
def root():
    return jsonify(status="ok", service="backend")


from .ton_routes import bp as ton_bp
from .telegram_auth import bp as tg_auth_bp
from .markets import bp as markets_bp
from .db import init_db

app.register_blueprint(ton_bp)
app.register_blueprint(tg_auth_bp)
app.register_blueprint(markets_bp)

init_db()
