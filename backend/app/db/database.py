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
    """Try PostgreSQL first; fall back to SQLite if unreachable."""
    if _is_postgres:
        try:
            _pool_kwargs = {
                "pool_size":     5,
                "max_overflow":  10,
                "pool_timeout":  5,
                "pool_recycle":  3600,
                "pool_pre_ping": True,
            }
            eng = create_engine(
                DATABASE_URL,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
                **_pool_kwargs,
            )
            # Test connection
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("[DB] Connected to PostgreSQL: %s", DATABASE_URL[:40])
            return eng, False
        except Exception as e:
            log.warning(
                "[DB] PostgreSQL unavailable (%s) — falling back to SQLite: %s",
                type(e).__name__, SQLITE_URL
            )

    # SQLite fallback
    eng = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    log.info("[DB] Using SQLite fallback: %s", SQLITE_URL)
    return eng, True


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
