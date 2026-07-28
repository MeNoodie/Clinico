"""SQLAlchemy configuration for the local SQLite database."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


import os

DATABASE_PATH = Path(os.getenv("SQLITE_DB_PATH", (Path(__file__).resolve().parent / "clinico.db").as_posix()))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
