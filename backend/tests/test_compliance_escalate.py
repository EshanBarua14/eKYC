"""
Tests for BFIU §4.3 STR escalation endpoint.
POST /api/v1/compliance/edd-cases/{id}/escalate-bfiu
"""
import pytest
import requests

BASE = "http://localhost:8000"

def _skip_if_no_server():
    try:
        requests.get(f"{BASE}/health", timeout=2)
    except Exception:
        pytest.skip("Backend not running")

def _get_token(email, password):
    r = requests.post(f"{BASE}/api/v1/auth/token",
                      json={"email": email, "password": password}, timeout=5)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]

def test_escalate_bfiu_no_auth():
    _skip_if_no_server()
    r = requests.post(f"{BASE}/api/v1/compliance/edd-cases/test-123/escalate-bfiu", timeout=5)
    assert r.status_code in (401, 403)

def test_escalate_bfiu_endpoint_exists():
    _skip_if_no_server()
    r = requests.post(f"{BASE}/api/v1/compliance/edd-cases/test-123/escalate-bfiu", timeout=5)
    assert r.status_code != 404, "Endpoint missing — 404 returned"

def test_escalate_bfiu_agent_forbidden():
    _skip_if_no_server()
    token = _get_token("agent-bypass@demo.ekyc", "DemoAgent@2026")
    r = requests.post(
        f"{BASE}/api/v1/compliance/edd-cases/abc-123/escalate-bfiu",
        headers={"Authorization": f"Bearer {token}"}, timeout=5,
    )
    assert r.status_code == 403
    # error boundary wraps as {"error": {...}}
    body = r.json()
    msg = body.get("error", {}).get("message", "") or body.get("detail", {}).get("message", "")
    assert "COMPLIANCE_OFFICER" in msg, f"Expected role message, got: {body}"

def test_escalate_bfiu_compliance_officer_succeeds():
    _skip_if_no_server()
    token = _get_token("co-bypass@demo.ekyc", "DemoCO@2026")
    r = requests.post(
        f"{BASE}/api/v1/compliance/edd-cases/abc-123/escalate-bfiu",
        headers={"Authorization": f"Bearer {token}"}, timeout=5,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["escalated"] is True
    assert data["str_reference"].startswith("STR-")
    assert "next_steps" in data
    assert "bfiu_ref" in data
