"""SQLAlchemy engine/session setup. Defaults to SQLite, but works with
PostgreSQL too by setting DATABASE_URL (e.g. postgresql+psycopg2://...),
per the project brief's "SQLite or PostgreSQL" option.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/app.db")

if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    # Relative sqlite path - make sure the containing directory exists
    # regardless of where the process was launched from.
    relative_path = DATABASE_URL.removeprefix("sqlite:///")
    db_dir = os.path.dirname(relative_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
