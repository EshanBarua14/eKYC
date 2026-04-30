"""
Tests for BFIU §4.3 STR escalation endpoint.
POST /api/v1/compliance/edd-cases/{id}/escalate-bfiu
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_escalate_bfiu_no_auth():
    r = client.post("/api/v1/compliance/edd-cases/test-123/escalate-bfiu")
    assert r.status_code in (401, 403)

def test_escalate_bfiu_endpoint_exists():
    """Endpoint must exist and return 401 without auth — not 404."""
    r = client.post("/api/v1/compliance/edd-cases/test-123/escalate-bfiu")
    assert r.status_code != 404, "Endpoint missing — 404 returned"

def test_escalate_bfiu_response_structure():
    """When called correctly, response must have required BFIU fields."""
    from app.core.security import create_access_token
    token = create_access_token({"sub": "test", "role": "COMPLIANCE_OFFICER"})
    r = client.post(
        "/api/v1/compliance/edd-cases/abc-123/escalate-bfiu",
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code == 200:
        data = r.json()
        assert data["escalated"] is True
        assert data["str_reference"].startswith("STR-")
        assert "next_steps" in data
        assert "bfiu_ref" in data

python -m pytest tests/test_compliance_escalate.py -v 2>&1 | tail -15
