import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------- CONFIG ----------

def get_postgres_url() -> str:
    """
    Строка подключения к Postgres.
    Синхронизировано с /opt/truestake/.env и docker-compose.yml.
    """
    url = os.getenv("POSTGRES_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "truestake")
    password = os.getenv("POSTGRES_PASSWORD", "truestake_pass")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "truestake_db")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


POSTGRES_URL = get_postgres_url()

engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

# ---------- MODELS ----------

class User(Base):
    """
    Модель под существующую таблицу users:
    id, username, telegram_id
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=True)


class Market(Base):
    """
    Черновая модель рынка — трогать не будем.
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


def init_db():
    """
    Создаёт таблицы, если их нет. Ничего не дропает.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("[init_db] Database initialized")
    except Exception as e:
        print(f"[init_db] Skip init: {e}")
