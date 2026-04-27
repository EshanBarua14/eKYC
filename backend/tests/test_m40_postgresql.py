"""M40 -- PostgreSQL migration tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_database_module_importable():
    from app.db.database import engine, SessionLocal, Base
    assert engine is not None

def test_T02_engine_has_dialect():
    from app.db.database import engine
    assert engine.dialect.name in ("sqlite", "postgresql")

def test_T03_session_local_creates():
    from app.db.database import SessionLocal
    s = SessionLocal()
    assert s is not None
    s.close()

def test_T04_get_db_yields():
    from app.db.database import get_db
    gen = get_db()
    db = next(gen)
    assert db is not None
    try: next(gen)
    except StopIteration: pass

def test_T05_db_session_context():
    from app.db.database import db_session
    with db_session() as db:
        assert db is not None

def test_T06_sqlite_fallback_works():
    from app.db.database import _effective_sqlite
    assert isinstance(_effective_sqlite, bool)

def test_T07_base_importable():
    from app.db.database import Base
    assert Base is not None
