"""
M10 - KYC Lifecycle Management Tests
Tests: periodic review, self-declaration, upgrade, closure, API endpoints
"""
import pytest
from fastapi.testclient import TestClient


class TestPeriodicReview:
    def setup_method(self):
        from app.services.lifecycle_service import (
            register_profile, get_due_reviews, complete_review,
            calculate_next_review, reset_lifecycle,
            REVIEW_FREQUENCY_YEARS, NOTIFICATION_DAYS_BEFORE,
        )
        self.register   = register_profile
        self.due        = get_due_reviews
        self.complete   = complete_review
        self.next_review = calculate_next_review
        self.reset      = reset_lifecycle
        self.FREQ       = REVIEW_FREQUENCY_YEARS
        self.NOTIFY     = NOTIFICATION_DAYS_BEFORE
        self.reset()

    def test_review_freq_high_1yr(self):
        assert self.FREQ["HIGH"] == 1

    def test_review_freq_medium_2yr(self):
        assert self.FREQ["MEDIUM"] == 2

    def test_review_freq_low_5yr(self):
        assert self.FREQ["LOW"] == 5

    def test_register_sets_next_review(self):
        p = self.register("p-001", "SIMPLIFIED", "LOW", "RAHMAN HOSSAIN", "+8801712345678")
        assert "next_review" in p
        assert p["review_years"] == 5

    def test_high_risk_next_review_1yr(self):
        p = self.register("p-002", "REGULAR", "HIGH", "RAHMAN HOSSAIN", "+8801712345678")
        assert p["review_years"] == 1

    def test_due_reviews_overdue_detected(self):
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        self.register("p-003", "REGULAR", "HIGH", "OVERDUE PERSON", "+8801712345678", opened_at=past)
        due = self.due(days_ahead=30)
        assert any(d["profile_id"] == "p-003" for d in due)

    def test_fresh_profile_not_due(self):
        self.register("p-004", "SIMPLIFIED", "LOW", "FRESH PERSON", "+8801712345678")
        due = self.due(days_ahead=30)
        assert not any(d["profile_id"] == "p-004" for d in due)

    def test_complete_review_updates_dates(self):
        self.register("p-005", "REGULAR", "MEDIUM", "REVIEW PERSON", "+8801712345678")
        r = self.complete("p-005")
        assert r["success"] is True
        assert "next_review" in r

    def test_complete_review_unknown_profile(self):
        r = self.complete("nonexistent")
        assert r["success"] is False

    def test_notification_days_high_30(self):
        assert self.NOTIFY["HIGH"] == 30

    def test_notification_days_low_60(self):
        assert self.NOTIFY["LOW"] == 60


class TestSelfDeclaration:
    def setup_method(self):
        from app.services.lifecycle_service import (
            register_profile, generate_declaration_token,
            submit_declaration, get_declaration,
            reset_lifecycle, DECLARATION_TOKEN_TTL_HOURS,
        )
        self.register  = register_profile
        self.generate  = generate_declaration_token
        self.submit    = submit_declaration
        self.get_decl  = get_declaration
        self.reset     = reset_lifecycle
        self.TTL       = DECLARATION_TOKEN_TTL_HOURS
        self.reset()
        self.register("p-decl", "SIMPLIFIED", "LOW", "DECL PERSON", "+8801712345678")

    def test_token_ttl_is_48hrs(self):
        assert self.TTL == 48

    def test_generate_returns_token(self):
        r = self.generate("p-decl", "+8801712345678")
        assert "token" in r
        assert len(r["token"]) > 10

    def test_generate_has_expires_at(self):
        r = self.generate("p-decl", "+8801712345678")
        assert "expires_at" in r

    def test_generate_has_declaration_url(self):
        r = self.generate("p-decl", "+8801712345678")
        assert "declaration_url" in r
        assert r["token"] in r["declaration_url"]

    def test_submit_valid_token(self):
        gen = self.generate("p-decl", "+8801712345678")
        r   = self.submit(gen["token"], "DECL PERSON", "1234567890123", "+8801712345678")
        assert r["success"] is True

    def test_submit_invalid_token(self):
        r = self.submit("invalid-token", "DECL PERSON", "1234567890123", "+8801712345678")
        assert r["success"] is False

    def test_submit_twice_fails(self):
        gen = self.generate("p-decl", "+8801712345678")
        self.submit(gen["token"], "DECL PERSON", "1234567890123", "+8801712345678")
        r = self.submit(gen["token"], "DECL PERSON", "1234567890123", "+8801712345678")
        assert r["success"] is False

    def test_bfiu_ref_in_result(self):
        gen = self.generate("p-decl", "+8801712345678")
        r   = self.submit(gen["token"], "DECL PERSON", "1234567890123", "+8801712345678")
        assert "5.7" in r["bfiu_ref"]


class TestUpgrade:
    def setup_method(self):
        from app.services.lifecycle_service import (
            register_profile, initiate_upgrade,
            complete_upgrade, get_profile, reset_lifecycle,
        )
        self.register  = register_profile
        self.initiate  = initiate_upgrade
        self.complete  = complete_upgrade
        self.get       = get_profile
        self.reset     = reset_lifecycle
        self.reset()
        self.register("p-upg", "SIMPLIFIED", "LOW", "UPGRADE PERSON", "+8801712345678")
        self.register("p-reg", "REGULAR",    "HIGH", "REGULAR PERSON", "+8801712345678")

    def test_initiate_upgrade_success(self):
        r = self.initiate("p-upg", "Product upgrade", "agent-001")
        assert r["success"] is True
        assert r["from_type"] == "SIMPLIFIED"
        assert r["to_type"]   == "REGULAR"

    def test_initiate_already_regular_fails(self):
        r = self.initiate("p-reg", "Upgrade", "agent-001")
        assert r["success"] is False

    def test_initiate_unknown_profile_fails(self):
        r = self.initiate("nonexistent", "Upgrade", "agent-001")
        assert r["success"] is False

    def test_initiate_has_required_fields(self):
        r = self.initiate("p-upg", "Product upgrade", "agent-001")
        assert "additional_info_required" in r
        assert "source_of_funds" in r["additional_info_required"]

    def test_complete_upgrade_changes_type(self):
        init = self.initiate("p-upg", "Product upgrade", "agent-001")
        r    = self.complete(init["upgrade_id"], {"source_of_funds": "Employment", "tin": "123456789"})
        assert r["success"] is True
        assert r["new_type"] == "REGULAR"

    def test_profile_type_updated_after_upgrade(self):
        init = self.initiate("p-upg", "Product upgrade", "agent-001")
        self.complete(init["upgrade_id"], {"source_of_funds": "Business"})
        profile = self.get("p-upg")
        assert profile["kyc_type"] == "REGULAR"

    def test_complete_twice_fails(self):
        init = self.initiate("p-upg", "Product upgrade", "agent-001")
        self.complete(init["upgrade_id"], {"source_of_funds": "Employment"})
        r = self.complete(init["upgrade_id"], {"source_of_funds": "Employment"})
        assert r["success"] is False

    def test_bfiu_ref_section_56(self):
        r = self.initiate("p-upg", "Product upgrade", "agent-001")
        assert "5.6" in r["bfiu_ref"]


class TestAccountClosure:
    def setup_method(self):
        from app.services.lifecycle_service import (
            register_profile, close_account,
            get_profile, reset_lifecycle,
        )
        self.register = register_profile
        self.close    = close_account
        self.get      = get_profile
        self.reset    = reset_lifecycle
        self.reset()
        self.register("p-close", "REGULAR", "HIGH", "CLOSE PERSON", "+8801712345678")

    def test_close_sets_status_closed(self):
        r = self.close("p-close", "Customer request")
        assert r["success"] is True
        assert r["status"] == "CLOSED"

    def test_close_sets_retention_5yrs(self):
        r = self.close("p-close", "Customer request")
        assert "retention_until" in r
        from datetime import datetime, timezone
        retention = datetime.fromisoformat(r["retention_until"])
        now       = datetime.now(timezone.utc)
        years     = (retention - now).days / 365
        assert 4.9 < years < 5.1

    def test_close_unknown_profile_fails(self):
        r = self.close("nonexistent", "reason")
        assert r["success"] is False

    def test_profile_status_closed_after(self):
        self.close("p-close", "Customer request")
        p = self.get("p-close")
        assert p["status"] == "CLOSED"

    def test_bfiu_ref_section_51(self):
        r = self.close("p-close", "Customer request")
        assert "5.1" in r["bfiu_ref"]


class TestLifecycleAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        self.client.post("/api/v1/auth/register", json={
            "email": "admin_lc@demo.com", "phone": "+8801712345678",
            "full_name": "Lifecycle Admin", "role": "ADMIN", "password": "admin1234",
        })
        import pyotp as _p10; _SS10 = "JBSWY3DPEHPK3PXP"
        from app.api.v1.routes.auth import _demo_users
        _uu10 = next((x for x in _demo_users if x.email == "admin_lc@demo.com"), None)
        if _uu10 and not _uu10.totp_enabled: _uu10.totp_secret = _SS10; _uu10.totp_enabled = True
        r = self.client.post("/api/v1/auth/token", json={
            "email": "admin_lc@demo.com", "password": "admin1234",
            "totp_code": _p10.TOTP(_SS10).now(),
        })
        self.token   = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        from app.services.lifecycle_service import reset_lifecycle
        reset_lifecycle()

    def test_register_profile(self):
        r = self.client.post("/api/v1/lifecycle/register", json={
            "profile_id": "api-p-001", "kyc_type": "SIMPLIFIED",
            "risk_grade": "LOW", "full_name": "API PERSON",
            "mobile": "+8801712345678",
        }, headers=self.headers)
        assert r.status_code == 201
        assert r.json()["profile_id"] == "api-p-001"

    def test_due_reviews_endpoint(self):
        r = self.client.get("/api/v1/lifecycle/due-reviews", headers=self.headers)
        assert r.status_code == 200
        assert "due_reviews" in r.json()

    def test_policy_endpoint(self):
        r = self.client.get("/api/v1/lifecycle/policy", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["data_retention_years"] == 5
        assert data["review_frequency_years"]["HIGH"] == 1

    def test_generate_declaration(self):
        self.client.post("/api/v1/lifecycle/register", json={
            "profile_id": "api-p-002", "kyc_type": "SIMPLIFIED",
            "risk_grade": "LOW", "full_name": "DECL PERSON",
            "mobile": "+8801712345678",
        }, headers=self.headers)
        r = self.client.post("/api/v1/lifecycle/declare/generate", json={
            "profile_id": "api-p-002", "mobile": "+8801712345678",
        }, headers=self.headers)
        assert r.status_code == 201
        assert "token" in r.json()

    def test_submit_declaration(self):
        self.client.post("/api/v1/lifecycle/register", json={
            "profile_id": "api-p-003", "kyc_type": "SIMPLIFIED",
            "risk_grade": "LOW", "full_name": "DECL PERSON 3",
            "mobile": "+8801712345678",
        }, headers=self.headers)
        gen = self.client.post("/api/v1/lifecycle/declare/generate", json={
            "profile_id": "api-p-003", "mobile": "+8801712345678",
        }, headers=self.headers)
        token = gen.json()["token"]
        r = self.client.post(f"/api/v1/lifecycle/declare/{token}", json={
            "full_name": "DECL PERSON 3",
            "nid_number": "1234567890123",
            "contact_number": "+8801712345678",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_upgrade_flow(self):
        self.client.post("/api/v1/lifecycle/register", json={
            "profile_id": "api-p-004", "kyc_type": "SIMPLIFIED",
            "risk_grade": "LOW", "full_name": "UPGRADE PERSON",
            "mobile": "+8801712345678",
        }, headers=self.headers)
        r = self.client.post("/api/v1/lifecycle/upgrade/initiate", json={
            "profile_id": "api-p-004", "reason": "Product upgrade",
            "requested_by": "agent-001",
        }, headers=self.headers)
        assert r.status_code == 201
        upgrade_id = r.json()["upgrade_id"]
        r2 = self.client.post("/api/v1/lifecycle/upgrade/complete", json={
            "upgrade_id": upgrade_id,
            "additional_info": {"source_of_funds": "Employment"},
        }, headers=self.headers)
        assert r2.status_code == 200
        assert r2.json()["new_type"] == "REGULAR"

    def test_close_account(self):
        self.client.post("/api/v1/lifecycle/register", json={
            "profile_id": "api-p-005", "kyc_type": "REGULAR",
            "risk_grade": "HIGH", "full_name": "CLOSE PERSON",
            "mobile": "+8801712345678",
        }, headers=self.headers)
        r = self.client.post("/api/v1/lifecycle/close", json={
            "profile_id": "api-p-005", "reason": "Customer request",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["status"] == "CLOSED"

    def test_unauthenticated_fails(self):
        r = self.client.get("/api/v1/lifecycle/due-reviews")
        assert r.status_code == 403
