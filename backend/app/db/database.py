"""
Database connection — PostgreSQL (production) with SQLite fallback (dev/CI)
BFIU Circular No. 29 — data residency on local server
M40: PostgreSQL migration
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL required — no SQLite in production
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://ekyc_user:ekyc_pass@localhost:5432/ekyc_db"
)

_is_sqlite   = DATABASE_URL.startswith("sqlite")
_is_postgres = DATABASE_URL.startswith("postgresql")

_connect_args = {"check_same_thread": False} if _is_sqlite else {}

_pool_kwargs: dict = {}
if _is_postgres:
    _pool_kwargs = {
        "pool_size":     5,
        "max_overflow":  10,
        "pool_timeout":  30,
        "pool_recycle":  3600,
        "pool_pre_ping": True,
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    **_pool_kwargs,
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


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
    """Context manager for use outside FastAPI (services, Celery, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def tenant_session(schema: str = "public"):
    """
    Opens a session scoped to a specific PostgreSQL schema.
    Falls back gracefully on SQLite (schema param ignored).
    """
    db = SessionLocal()
    try:
        if _is_postgres:
            db.execute(text(f"SET search_path TO {schema}, public"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables. Use Alembic for production migrations."""
    from app.db import models       # noqa — registers all models
    import app.db.models_platform   # noqa
    Base.metadata.create_all(bind=engine)
