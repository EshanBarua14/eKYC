"""
Fake EC API — Pytest test suite
Covers: auth, verify, verify/dob, error paths, audit log, admin endpoints.
Run: pytest fake_ec_api/test_fake_ec_api.py -v
"""
import pytest
from fastapi.testclient import TestClient
from database import create_tables, seed, get_db, NIDRecord, Institution, AuditLog, engine, SessionLocal, Base
from main import app

# ── Test DB setup ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create tables and seed data once per test session."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed(db)
    db.close()
    yield
    # teardown: drop only audit log rows (keep NIDs for inspection)
    db = SessionLocal()
    db.query(AuditLog).delete()
    db.commit()
    db.close()

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(scope="session")
def token(client):
    """Get a valid bearer token once per session."""
    r = client.post("/api/v1/auth", json={
        "client_id":     "inst_xpert_001",
        "client_secret": "sk_test_xpert_ekyc_secret_2026",
    })
    assert r.status_code == 200
    return r.json()["access_token"]

@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── System endpoints ──────────────────────────────────────────────────────

class TestSystem:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_status(self, client):
        r = client.get("/api/v1/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "OPERATIONAL"
        assert d["nid_records"]["total"] >= 9
        assert d["nid_records"]["active"] >= 8
        assert d["nid_records"]["blocked"] >= 1


# ── Auth ──────────────────────────────────────────────────────────────────

class TestAuth:
    def test_valid_credentials(self, client):
        r = client.post("/api/v1/auth", json={
            "client_id":     "inst_xpert_001",
            "client_secret": "sk_test_xpert_ekyc_secret_2026",
        })
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d
        assert d["token_type"] == "Bearer"
        assert d["expires_in"] == 3600
        assert d["institution_name"] == "Xpert Fintech Ltd."

    def test_second_institution(self, client):
        r = client.post("/api/v1/auth", json={
            "client_id":     "inst_test_bank",
            "client_secret": "sk_test_bank_secret_2026",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_wrong_secret(self, client):
        r = client.post("/api/v1/auth", json={
            "client_id":     "inst_xpert_001",
            "client_secret": "wrong_secret",
        })
        assert r.status_code == 401
        assert r.json()["detail"]["error_code"] == "EC_AUTH_ERROR"

    def test_unknown_client(self, client):
        r = client.post("/api/v1/auth", json={
            "client_id":     "unknown_client",
            "client_secret": "anything",
        })
        assert r.status_code == 401

    def test_suspended_institution(self, client):
        r = client.post("/api/v1/auth", json={
            "client_id":     "inst_suspended",
            "client_secret": "sk_suspended_secret",
        })
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "INSTITUTION_SUSPENDED"

    def test_no_token_on_verify(self, client):
        r = client.post("/api/v1/verify", json={"nid_number": "2375411929"})
        assert r.status_code == 403  # FastAPI HTTPBearer returns 403 when no header

    def test_invalid_token(self, client):
        r = client.post(
            "/api/v1/verify",
            json={"nid_number": "2375411929"},
            headers={"Authorization": "Bearer fake_token_xyz"},
        )
        assert r.status_code == 401
        assert r.json()["detail"]["error_code"] == "EC_AUTH_ERROR"


# ── Verify NID ────────────────────────────────────────────────────────────

class TestVerifyNID:
    def test_eshan_barua(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "2375411929", "session_id": "test_s1"},
                        headers=auth)
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["nid_number"] == "2375411929"
        assert d["source"] == "EC_FAKE_TEST"
        assert d["data"]["full_name_en"] == "ESHAN BARUA"
        assert d["data"]["date_of_birth"] == "1994-08-14"
        assert d["data"]["gender"] == "M"
        assert d["data"]["blood_group"] == "O+"
        assert d["data"]["fathers_name_en"] == "PRODIP BARUA"
        assert d["data"]["mothers_name_en"] == "SHIMA BARUA"
        assert d["data"]["status"] == "ACTIVE"
        assert "BFIU" in d["bfiu_ref"]

    def test_fatema_begum(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "9876543210987"}, headers=auth)
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["full_name_en"] == "FATEMA BEGUM"
        assert d["gender"] == "F"
        assert d["spouse_name_en"] == "MD KARIM"

    def test_17digit_nid(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "19858524905063671"}, headers=auth)
        assert r.status_code == 200
        assert r.json()["data"]["full_name_en"] == "MD ABUL MOSHAD CHOWDHURY"

    def test_all_seeded_nids_found(self, client, auth):
        nids = [
            "2375411929", "19858524905063671", "1234567890123",
            "9876543210987", "1111111111111", "2222222222222",
            "3333333333333", "4444444444444",
        ]
        for nid in nids:
            r = client.post("/api/v1/verify", json={"nid_number": nid}, headers=auth)
            assert r.status_code == 200, f"NID {nid} failed: {r.text}"
            assert r.json()["success"] is True

    def test_not_found(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "9999999999999"}, headers=auth)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "EC_NOT_FOUND"

    def test_blocked_nid(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "0000000000000"}, headers=auth)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "NID_BLOCKED"

    def test_invalid_format_short(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "12345"}, headers=auth)
        assert r.status_code == 422
        assert r.json()["detail"]["error_code"] == "INVALID_NID_FORMAT"

    def test_invalid_format_letters(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "ABC1234567890"}, headers=auth)
        assert r.status_code == 422

    def test_nid_with_spaces_cleaned(self, client, auth):
        """NID with spaces should be cleaned and resolved."""
        r = client.post("/api/v1/verify",
                        json={"nid_number": "2375 411929"}, headers=auth)
        assert r.status_code == 200

    def test_session_id_returned(self, client, auth):
        r = client.post("/api/v1/verify",
                        json={"nid_number": "2375411929", "session_id": "my_session_xyz"},
                        headers=auth)
        assert r.json()["session_id"] == "my_session_xyz"


# ── Verify NID + DOB ──────────────────────────────────────────────────────

class TestVerifyDOB:
    def test_correct_dob(self, client, auth):
        r = client.post("/api/v1/verify/dob",
                        json={"nid_number": "2375411929", "date_of_birth": "1994-08-14"},
                        headers=auth)
        assert r.status_code == 200
        assert r.json()["dob_matched"] is True

    def test_wrong_dob(self, client, auth):
        r = client.post("/api/v1/verify/dob",
                        json={"nid_number": "2375411929", "date_of_birth": "1990-01-01"},
                        headers=auth)
        assert r.status_code == 422
        assert r.json()["detail"]["error_code"] == "DOB_MISMATCH"

    def test_not_found_with_dob(self, client, auth):
        r = client.post("/api/v1/verify/dob",
                        json={"nid_number": "9999999999999", "date_of_birth": "1990-01-01"},
                        headers=auth)
        assert r.status_code == 404

    def test_invalid_dob_format(self, client, auth):
        r = client.post("/api/v1/verify/dob",
                        json={"nid_number": "2375411929", "date_of_birth": "14-08-1994"},
                        headers=auth)
        assert r.status_code == 422

    def test_blocked_nid_with_dob(self, client, auth):
        r = client.post("/api/v1/verify/dob",
                        json={"nid_number": "0000000000000", "date_of_birth": "2000-01-01"},
                        headers=auth)
        assert r.status_code == 403


# ── GET endpoint ──────────────────────────────────────────────────────────

class TestGetNID:
    def test_get_valid(self, client, auth):
        r = client.get("/api/v1/verify/2375411929", headers=auth)
        assert r.status_code == 200
        assert r.json()["data"]["full_name_en"] == "ESHAN BARUA"

    def test_get_not_found(self, client, auth):
        r = client.get("/api/v1/verify/9999999999999", headers=auth)
        assert r.status_code == 404


# ── Admin endpoints ───────────────────────────────────────────────────────

class TestAdmin:
    def test_list_nids(self, client):
        r = client.get("/api/v1/nids")
        assert r.status_code == 200
        d = r.json()
        assert d["count"] >= 9
        nid_numbers = [n["nid_number"] for n in d["nids"]]
        assert "2375411929" in nid_numbers
        assert "0000000000000" in nid_numbers

    def test_seed_new_nid(self, client, auth):
        # Clean up in case prior run left it
        client.delete("/api/v1/nids/5555555555555")
        r = client.post("/api/v1/nids", json={
            "nid_number":    "5555555555555",
            "full_name_en":  "TEST PERSON",
            "full_name_bn":  "টেস্ট ব্যক্তি",
            "date_of_birth": "2000-06-15",
            "gender":        "M",
            "status":        "ACTIVE",
            "nid_type":      "SMART",
        })
        assert r.status_code == 201
        assert r.json()["seeded"] is True

        # Verify it's now findable
        r2 = client.post("/api/v1/verify", json={"nid_number": "5555555555555"}, headers=auth)
        assert r2.status_code == 200
        assert r2.json()["data"]["full_name_en"] == "TEST PERSON"

    def test_seed_duplicate_rejected(self, client):
        # seed the same NID twice
        client.post("/api/v1/nids", json={
            "nid_number": "6666666666666", "full_name_en": "DUP",
            "full_name_bn": "ডুপ", "date_of_birth": "2000-01-01", "gender": "M",
        })
        r = client.post("/api/v1/nids", json={
            "nid_number": "6666666666666", "full_name_en": "DUP",
            "full_name_bn": "ডুপ", "date_of_birth": "2000-01-01", "gender": "M",
        })
        assert r.status_code == 409

    def test_delete_nid(self, client, auth):
        # seed then delete
        client.post("/api/v1/nids", json={
            "nid_number": "7777777777777", "full_name_en": "DELETE ME",
            "full_name_bn": "ডিলিট", "date_of_birth": "2001-01-01", "gender": "F",
        })
        r = client.delete("/api/v1/nids/7777777777777")
        assert r.status_code == 200
        assert r.json()["deleted"] is True

        # confirm gone
        r2 = client.post("/api/v1/verify", json={"nid_number": "7777777777777"}, headers=auth)
        assert r2.status_code == 404

    def test_audit_log(self, client):
        r = client.get("/api/v1/audit?limit=20")
        assert r.status_code == 200
        d = r.json()
        assert "count" in d
        assert "entries" in d
        for e in d["entries"]:
            assert "institution_id" in e
            assert "nid_last4" in e
            assert "result" in e
