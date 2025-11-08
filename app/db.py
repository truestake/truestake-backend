import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# URL до PostgreSQL
# В Docker у нас хост postgres (из docker-compose)
# Локально можешь переопределить через переменную окружения POSTGRES_URL
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


def init_db():
    """
    Создаём таблицы. Если БД недоступна (например, локально без postgres),
    просто выводим предупреждение, но не роняем приложение.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("[init_db] Database initialized")
    except Exception as e:
        print(f"[init_db] Skip init: {e}")
