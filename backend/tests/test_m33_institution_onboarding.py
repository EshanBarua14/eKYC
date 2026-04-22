"""
test_m33_institution_onboarding.py - M33 Institution Onboarding Flow
Tests: application, review, approval, rejection, activation, suspension, stats
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.institution_onboarding_service import reset_applications

client = TestClient(app)
BASE = "/api/v1/institutions/onboard"
AUTH = "/api/v1/auth"

from tests.test_helpers import setup_totp_and_login

def ah():
    token = setup_totp_and_login(client, "admin_m33@test.com", "ADMIN")
    return {"Authorization": f"Bearer {token}"}

def audh():
    token = setup_totp_and_login(client, "auditor_m33@test.com", "AUDITOR")
    return {"Authorization": f"Bearer {token}"}

def apply(code="TESTINS", name=None, itype="insurance"):
    inst_name = name or f"Test Institution {code}"
    return client.post(f"{BASE}/apply", json={
        "name": inst_name, "short_code": code,
        "institution_type": itype,
        "contact_email": f"{code.lower()}@example.com",
        "contact_phone": "01700000000",
        "address": "123 Test Street, Dhaka",
        "license_number": f"LIC-{code}-2026",
    })

def setup_function():
    reset_applications()

# ══════════════════════════════════════════════════════════════════════════
# 1. Application submission (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestApplication:
    def setup_method(self): reset_applications()

    def test_apply_201(self):
        r = apply("INS001")
        assert r.status_code == 201

    def test_apply_has_app_id(self):
        r = apply("INS002")
        assert "app_id" in r.json()
        assert r.json()["app_id"].startswith("APP-")

    def test_apply_initial_status_applied(self):
        r = apply("INS003")
        assert r.json()["application"]["status"] == "APPLIED"

    def test_apply_duplicate_short_code_409(self):
        apply("INS004")
        r = apply("INS004", name="Different Name")
        assert r.status_code == 409

    def test_apply_invalid_type_409(self):
        r = client.post(f"{BASE}/apply", json={
            "name":"Bad Type","short_code":"BAD01",
            "institution_type":"invalid_xyz",
            "contact_email":"bad@test.com","contact_phone":"017"
        })
        assert r.status_code == 409

    def test_apply_stores_all_fields(self):
        r = apply("INS006")
        app = r.json()["application"]
        for f in ["name","short_code","institution_type","contact_email","status"]:
            assert f in app, f"Missing: {f}"

# ══════════════════════════════════════════════════════════════════════════
# 2. List & Get (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestListGet:
    def setup_method(self): reset_applications()

    def test_list_requires_auth(self):
        r = client.get(f"{BASE}/applications")
        assert r.status_code == 403

    def test_list_applications_200(self):
        apply("LST001"); apply("LST002")
        r = client.get(f"{BASE}/applications", headers=ah())
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_list_filter_by_status(self):
        apply("LST003")
        r = client.get(f"{BASE}/applications?status=APPLIED", headers=ah())
        assert all(a["status"] == "APPLIED" for a in r.json()["applications"])

    def test_get_application_by_id(self):
        r = apply("GET001")
        app_id = r.json()["app_id"]
        r2 = client.get(f"{BASE}/{app_id}", headers=ah())
        assert r2.status_code == 200
        assert r2.json()["application"]["app_id"] == app_id

    def test_get_nonexistent_404(self):
        r = client.get(f"{BASE}/NONEXISTENT", headers=ah())
        assert r.status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 3. Review flow (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestReview:
    def setup_method(self): reset_applications()

    def test_start_review_changes_status(self):
        r = apply("REV001")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/review", json={"note":"Looks good"}, headers=ah())
        assert r2.status_code == 200
        assert r2.json()["application"]["status"] == "UNDER_REVIEW"

    def test_review_requires_admin(self):
        r = apply("REV002")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/review", json={}, headers=audh())
        assert r2.status_code == 403

    def test_add_note_to_application(self):
        r = apply("REV003")
        app_id = r.json()["app_id"]
        client.post(f"{BASE}/{app_id}/review", json={}, headers=ah())
        r2 = client.post(f"{BASE}/{app_id}/note",
                         json={"note":"Additional verification needed"},
                         headers=ah())
        assert r2.status_code == 200
        assert len(r2.json()["application"]["notes"]) >= 1

    def test_cannot_review_approved_application(self):
        r = apply("REV004")
        app_id = r.json()["app_id"]
        client.post(f"{BASE}/{app_id}/approve", json={}, headers=ah())
        r2 = client.post(f"{BASE}/{app_id}/review", json={}, headers=ah())
        assert r2.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 4. Approval flow (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestApproval:
    def setup_method(self): reset_applications()

    def test_approve_creates_institution(self):
        r = apply("APR001")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/approve", json={}, headers=ah())
        assert r2.status_code == 201
        assert "institution_id" in r2.json()

    def test_approve_returns_client_credentials(self):
        r = apply("APR002")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/approve", json={}, headers=ah())
        assert "client_id" in r2.json()
        assert "client_secret" in r2.json()
        assert r2.json()["client_id"].startswith("client_")

    def test_approve_sets_status_approved(self):
        r = apply("APR003")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/approve", json={}, headers=ah())
        assert r2.json()["application"]["status"] == "APPROVED"

    def test_approve_generates_schema_name(self):
        r = apply("APR004")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/approve", json={}, headers=ah())
        assert r2.json()["schema_name"].startswith("tenant_")

    def test_cannot_approve_rejected(self):
        r = apply("APR005")
        app_id = r.json()["app_id"]
        client.post(f"{BASE}/{app_id}/reject",
                    json={"reason":"Incomplete docs"}, headers=ah())
        r2 = client.post(f"{BASE}/{app_id}/approve", json={}, headers=ah())
        assert r2.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 5. Rejection flow (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestRejection:
    def setup_method(self): reset_applications()

    def test_reject_sets_status(self):
        r = apply("REJ001")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/reject",
                         json={"reason":"Missing BFIU license"},
                         headers=ah())
        assert r2.status_code == 200
        assert r2.json()["application"]["status"] == "REJECTED"

    def test_reject_stores_reason(self):
        r = apply("REJ002")
        app_id = r.json()["app_id"]
        client.post(f"{BASE}/{app_id}/reject",
                    json={"reason":"Expired documents"}, headers=ah())
        r2 = client.get(f"{BASE}/{app_id}", headers=ah())
        assert "Expired documents" in r2.json()["application"]["rejection_reason"]

    def test_reject_requires_reason(self):
        r = apply("REJ003")
        app_id = r.json()["app_id"]
        r2 = client.post(f"{BASE}/{app_id}/reject", json={}, headers=ah())
        assert r2.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 6. Stats (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestStats:
    def setup_method(self): reset_applications()

    def test_stats_200(self):
        r = client.get(f"{BASE}/stats", headers=ah())
        assert r.status_code == 200

    def test_stats_has_pipeline(self):
        r = client.get(f"{BASE}/stats", headers=ah())
        d = r.json()
        assert "pipeline" in d
        assert "total_applications" in d
        assert "active_institutions" in d

    def test_stats_counts_correctly(self):
        apply("STA001"); apply("STA002")
        r = client.get(f"{BASE}/stats", headers=ah())
        assert r.json()["total_applications"] >= 2
        assert r.json()["pipeline"]["APPLIED"] >= 2
