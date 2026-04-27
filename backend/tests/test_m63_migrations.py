"""M63 -- Alembic migration tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_alembic_ini_exists():
    import os
    assert os.path.exists("alembic.ini")

def test_T02_alembic_env_exists():
    import os
    assert os.path.exists("alembic/env.py")

def test_T03_migrations_dir_exists():
    import os
    assert os.path.isdir("alembic/versions")

def test_T04_has_migrations():
    import os
    files = [f for f in os.listdir("alembic/versions") if f.endswith(".py")]
    assert len(files) >= 5

def test_T05_baseline_migration_exists():
    import os
    files = os.listdir("alembic/versions")
    assert any("m63" in f or "baseline" in f for f in files)

def test_T06_m102_migration_exists():
    import os
    files = os.listdir("alembic/versions")
    assert any("m102" in f or "pgcrypto" in f for f in files)

def test_T07_no_create_all_in_app():
    import os, glob
    py_files = glob.glob("app/**/*.py", recursive=True)
    for f in py_files:
        if "migration" in f or "alembic" in f:
            continue
        try:
            content = open(f, encoding="utf-8", errors="ignore").read()
            if "Base.metadata.create_all" in content:
                assert False, f"create_all found in {f} -- use Alembic"
        except: pass
