"""M95 -- API endpoint path fix tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_T01_auth_endpoint_exists():
    r = client.post("/api/v1/auth/token", json={})
    assert r.status_code != 404

def test_T02_kyc_profiles_endpoint():
    r = client.get("/api/v1/kyc/profiles")
    assert r.status_code in (401, 403, 422)

def test_T03_no_404_on_core_routes():
    core_routes = ["/api/v1/auth/token", "/api/v1/face/verify"]
    for route in core_routes:
        r = client.options(route)
        assert r.status_code != 404, f"Route not found: {route}"
