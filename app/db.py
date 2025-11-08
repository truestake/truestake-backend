import os
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    BigInteger,
)
from sqlalchemy.orm import declarative_base, sessionmaker


def get_postgres_url() -> str:
    url = os.getenv("POSTGRES_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "truestake")
    password = os.getenv("POSTGRES_PASSWORD", "truestake_pass")
    db = os.getenv("POSTGRES_DB", "truestake_db")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


POSTGRES_URL = get_postgres_url()

engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(64), unique=True, index=True, nullable=True)
    role = Column(String(16), nullable=False, default="user")


class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(255), nullable=False)  # текст события в одну строку
    category = Column(String(32), index=True, nullable=True)  # политика/спорт/...
    status = Column(String(16), index=True, default="pending")
    # pending (создан), active (в ленте), resolved, canceled

    resolution_ts = Column(DateTime, nullable=True, index=True)  # дедлайн события

    creator_telegram_id = Column(BigInteger, index=True, nullable=False)

    # для карточки, как на твоём скрине
    probability_yes = Column(Float, default=50.0)  # 0-100
    volume_usd = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("[init_db] Database initialized")
    except Exception as e:
        print(f"[init_db] Skip init: {e}")
