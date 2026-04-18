"""
test_consent.py - M16 Digital Consent Gate
Tests: record, get, verify, revoke, list, gate enforcement
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/consent"

SAMPLE = {
    "session_id":     "sess_consent_01",
    "nid_hash":       "abc123hash",
    "institution_id": "inst_01",
    "agent_id":       "agent_01",
    "channel":        "AGENCY",
}

class TestConsentRecord:
    def test_record_201(self):
        r = client.post(f"{BASE}/record", json={**SAMPLE,"session_id":"sess_c_r1"})
        assert r.status_code == 201

    def test_record_has_consent_fields(self):
        r = client.post(f"{BASE}/record", json={**SAMPLE,"session_id":"sess_c_r2"})
        c = r.json()["consent"]
        for k in ["consent_id","session_id","timestamp","status","bfiu_ref","ip_address"]:
            assert k in c, f"Missing: {k}"

    def test_record_status_granted(self):
        r = client.post(f"{BASE}/record", json={**SAMPLE,"session_id":"sess_c_r3"})
        assert r.json()["consent"]["status"] == "GRANTED"

    def test_record_idempotent(self):
        sid = "sess_c_idem"
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        r2 = client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        assert r2.status_code == 201
        assert r2.json()["already_recorded"] is True

    def test_record_bfiu_ref(self):
        r = client.post(f"{BASE}/record", json={**SAMPLE,"session_id":"sess_c_bfiu"})
        assert "BFIU" in r.json()["consent"]["bfiu_ref"]

class TestConsentGet:
    def test_get_existing(self):
        sid = "sess_c_get1"
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        r = client.get(f"{BASE}/{sid}")
        assert r.status_code == 200
        assert r.json()["consent"]["session_id"] == sid

    def test_get_nonexistent_404(self):
        assert client.get(f"{BASE}/nonexistent_session_xyz").status_code == 404

class TestConsentVerify:
    def test_verify_after_record(self):
        sid = "sess_c_v1"
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        r = client.post(f"{BASE}/verify", json={"session_id":sid})
        assert r.status_code == 200
        assert r.json()["consent_verified"] is True

    def test_verify_without_record_403(self):
        r = client.post(f"{BASE}/verify", json={"session_id":"sess_no_consent_xyz"})
        assert r.status_code == 403

    def test_verify_returns_consent_id(self):
        sid = "sess_c_v2"
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        r = client.post(f"{BASE}/verify", json={"session_id":sid})
        assert "consent_id" in r.json()

class TestConsentRevoke:
    def test_revoke_changes_status(self):
        sid = "sess_c_rev1"
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        r = client.post(f"{BASE}/{sid}/revoke")
        assert r.status_code == 200
        assert r.json()["status"] == "REVOKED"

    def test_verify_after_revoke_403(self):
        sid = "sess_c_rev2"
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":sid})
        client.post(f"{BASE}/{sid}/revoke")
        r = client.post(f"{BASE}/verify", json={"session_id":sid})
        assert r.status_code == 403

class TestConsentList:
    def test_list_200(self):
        assert client.get(f"{BASE}/list/all").status_code == 200

    def test_list_after_record(self):
        client.post(f"{BASE}/record", json={**SAMPLE,"session_id":"sess_c_list1"})
        r = client.get(f"{BASE}/list/all")
        assert r.json()["total"] >= 1
