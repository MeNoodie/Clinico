"""SQLAlchemy configuration for the local SQLite database."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


import os

DATABASE_PATH = Path(os.getenv("SQLITE_DB_PATH", (Path(__file__).resolve().parent / "clinico.db").as_posix()))
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Render provides postgres:// URLs; SQLAlchemy should use the psycopg 3
    # dialect explicitly. Also accept the standard postgresql:// form.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://", "postgresql+psycopg://", 1
        )
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
else:
    DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


class Base(DeclarativeBase):
    """Base class for all ORM models."""


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
