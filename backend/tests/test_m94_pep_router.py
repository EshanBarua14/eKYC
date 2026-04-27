"""M94 -- PEP router prefix fix tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_T01_pep_entries_endpoint_exists():
    from app.api.v1.router import v1_router
    paths = [r.path for r in v1_router.routes]
    assert any("pep" in p for p in paths)

def test_T02_no_double_v1_prefix():
    from app.api.v1.router import v1_router
    for r in v1_router.routes:
        assert "/v1/v1/" not in r.path, f"Double v1 prefix: {r.path}"

def test_T03_pep_endpoint_auth_required():
    r = client.get("/api/v1/pep/entries")
    assert r.status_code in (401, 403, 422)
