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
from sqlalchemy.orm import sessionmaker, declarative_base

# --------------------------------------
# Подключение к PostgreSQL
# --------------------------------------

def get_postgres_url() -> str:
    """
    Собираем строку подключения к Postgres.
    Если есть POSTGRES_URL — используем её.
    Иначе — собираем из HOST/PORT/USER/PASSWORD/DB.
    """
    url = os.getenv("POSTGRES_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "truestake")
    password = os.getenv("POSTGRES_PASSWORD", "truestake_pass")
    db = os.getenv("POSTGRES_DB", "truestake_db")
    host = os.getenv("POSTGRES_HOST", "infra-postgres-1")
    port = os.getenv("POSTGRES_PORT", "5432")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


POSTGRES_URL = get_postgres_url()

engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

# --------------------------------------
# Модели
# --------------------------------------


class User(Base):
    """
    Пользователь, авторизованный через Telegram.
    Поле role:
      - user
      - creator
      - admin
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    role = Column(String(16), nullable=False, default="user")


class Market(Base):
    """
    Рынок / событие для предсказаний.
    """
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)

    # Основное
    question = Column(String(255), nullable=False)
    category = Column(String(32), nullable=True)  # politics / economy / crypto / ...
    status = Column(String(16), nullable=False, default="pending")  # pending/active/resolved

    # Когда узнаём исход
    resolution_ts = Column(DateTime, nullable=True)

    # Кто создал (по Telegram ID)
    creator_telegram_id = Column(BigInteger, nullable=False, default=0)

    # Текущая оценка вероятности "YES"
    probability_yes = Column(Float, nullable=False, default=50.0)

    # Объём торгов в USD (пока просто число)
    volume_usd = Column(Float, nullable=False, default=0.0)

    # Визуал и источник правды
    logo_url = Column(String(255), nullable=True)
    resolution_source = Column(Text, nullable=True)

    # Таймстемпы
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


def init_db():
    """
    Создаём таблицы, если их нет.
    Ничего не трогает в уже существующих (кроме добавления недостающих таблиц/полей).
    """
    Base.metadata.create_all(bind=engine)
    print("[init_db] Database initialized", flush=True)
