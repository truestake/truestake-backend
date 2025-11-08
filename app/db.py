import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Float,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------- CONFIG ----------

def get_postgres_url() -> str:
    """
    Строим строку подключения к Postgres из переменных окружения.
    Использует те же значения, что заданы в /opt/truestake/.env.
    """
    url = os.getenv("POSTGRES_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "truestake")
    password = os.getenv("POSTGRES_PASSWORD", "truestake_pwd")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "truestake")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


POSTGRES_URL = get_postgres_url()

engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

# ---------- MODELS ----------

class User(Base):
    """
    Пользователь TrueStake, привязан к Telegram.
    Используем telegram_id как основной идентификатор.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    username = Column(String(64), nullable=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    language_code = Column(String(8), nullable=True)
    is_premium = Column(String(8), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Market(Base):
    """
    Черновая модель рынка. Сейчас не трогаем логику,
    только сохраняем как есть, чтобы не ломать.
    """
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="open", index=True)
    outcome_yes_price = Column(Float, default=0.5)
    outcome_no_price = Column(Float, default=0.5)
    creator_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- INIT ----------

def init_db():
    """
    Создаём таблицы, если их ещё нет.
    Вызывается из app.__init__.py один раз при старте.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("[init_db] Database initialized")
    except Exception as e:
        print(f"[init_db] Skip init: {e}")
