from flask import Flask, jsonify
from flask_cors import CORS

from .ton_routes import bp as ton_bp
from .telegram_auth import bp as tg_auth_bp
from .markets import bp as markets_bp
from .db import init_db

app = Flask(__name__)

# CORS для Mini App:
# Разрешаем фронту (https://app.corsarinc.ru) ходить:
# - в /auth/telegram (авторизация)
# - в /auth/me       (проверка токена)
# - во все /markets  (лента, создание, модерация)
CORS(
    app,
    resources={
        r"/auth/telegram": {
            "origins": ["https://app.corsarinc.ru"]
        },
        r"/auth/me": {
            "origins": ["https://app.corsarinc.ru"]
        },
        r"/markets*": {
            "origins": ["https://app.corsarinc.ru"]
        },
    },
)

@app.get("/")
def root():
    return jsonify(status="ok", service="backend")

# Регистрируем все блюпринты
app.register_blueprint(ton_bp)
app.register_blueprint(tg_auth_bp)
app.register_blueprint(markets_bp)

# Инициализация БД (создание таблиц, если нет)
init_db()
