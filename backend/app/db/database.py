"""
Database connection — SQLite for dev, PostgreSQL for production
BFIU Circular No. 29 — data residency on local server
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ekyc.db")

_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,           # detect stale connections
    pool_recycle=3600,            # recycle connections every hour
    echo=os.getenv("SQL_ECHO","false").lower() == "true",
)

# Enable WAL mode for SQLite (better concurrent reads)
if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    """FastAPI dependency — yields DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session():
    """Context manager for use outside FastAPI (services, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Create all tables (dev / testing). Use Alembic in production."""
    from app.db import models  # noqa — registers all models
    Base.metadata.create_all(bind=engine)
