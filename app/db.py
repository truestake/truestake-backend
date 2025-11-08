import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker


POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://truestake:truestake_pwd@postgres:5432/truestake",
)

engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=True)


class Market(Base):
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
    try:
        Base.metadata.create_all(bind=engine)
        print("[init_db] Database initialized")
    except Exception as e:
        print(f"[init_db] Skip init: {e}")
