"""
Global test configuration.
Unit tests run with SQLite. Tests requiring PostgreSQL skip when DB unavailable.
Integration tests: INTEGRATION_TESTS=1
"""
import os
import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: real DB + Redis tests (set INTEGRATION_TESTS=1)"
    )

# ── DB availability check ────────────────────────────────────────────────────
def _postgres_available() -> bool:
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("postgresql"):
        return False
    try:
        import psycopg2
        from urllib.parse import urlparse
        p = urlparse(db_url)
        conn = psycopg2.connect(
            host=p.hostname, port=p.port or 5432,
            user=p.username, password=p.password,
            dbname=p.path.lstrip("/"),
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False

POSTGRES_AVAILABLE = _postgres_available()

# ── Autoskip fixture for tests that need real PostgreSQL ─────────────────────
@pytest.fixture(autouse=True)
def skip_if_no_postgres(request):
    """
    Auto-skip tests that use TestClient (which hits real DB via app startup)
    when PostgreSQL is not available.
    """
    if POSTGRES_AVAILABLE:
        return
    if os.getenv("INTEGRATION_TESTS") == "1":
        return
    # Check if test uses 'client' fixture or imports from app.main
    markers = [m.name for m in request.node.iter_markers()]
    if "integration" in markers:
        pytest.skip("PostgreSQL not available — set INTEGRATION_TESTS=1")
        return
    # Check test module for TestClient usage
    module = request.node.fspath
    try:
        with open(str(module), encoding="utf-8") as f:
            src = f.read()
        if "TestClient" in src and "from app.main import" in src:
            pytest.skip("PostgreSQL not available (TestClient test)")
    except Exception:
        pass
