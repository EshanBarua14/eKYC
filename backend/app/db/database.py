"""
Database connection — PostgreSQL (production) with SQLite fallback (dev/CI)
BFIU Circular No. 29 — data residency on local server
M40: PostgreSQL migration
"""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://ekyc_user:ekyc_pass@localhost:5432/ekyc_db"
)
SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./ekyc.db")

_is_sqlite   = DATABASE_URL.startswith("sqlite")
_is_postgres = DATABASE_URL.startswith("postgresql")


def _make_engine():
    """PostgreSQL only -- no SQLite fallback. BFIU data residency."""
    if not _is_postgres:
        raise RuntimeError(f"DATABASE_URL must be PostgreSQL. Got: {DATABASE_URL[:40]}")
    eng = create_engine(
        DATABASE_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("[DB] Connected to PostgreSQL: %s", DATABASE_URL[:40])
    return eng, False


engine, _fell_back_to_sqlite = _make_engine()
_effective_sqlite = _is_sqlite or _fell_back_to_sqlite

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
    engine.dispose()
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
        if not _effective_sqlite:
            db.execute(text(f"SET search_path TO {schema}, public"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    M63: Tables managed by Alembic migrations only.
    Run: alembic upgrade head
    create_all() removed - BFIU compliance requires versioned schema.
    """
    pass  # Alembic manages all schema changes
