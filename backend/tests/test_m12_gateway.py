"""
M12 - API Gateway Tests
Tests: rate limiting, data residency, webhooks, version, health, API
"""
import pytest
from fastapi.testclient import TestClient


class TestRateLimiting:
    def setup_method(self):
        from app.services.gateway_service import (
            check_rate_limit, reset_rate_limits, RATE_LIMITS,
        )
        self.check  = check_rate_limit
        self.reset  = reset_rate_limits
        self.LIMITS = RATE_LIMITS
        self.reset()

    def test_first_request_allowed(self):
        r = self.check("default", "client-001")
        assert r["allowed"] is True

    def test_count_increments(self):
        self.check("default", "client-002")
        r = self.check("default", "client-002")
        assert r["count"] == 2

    def test_remaining_decrements(self):
        r1 = self.check("default", "client-003")
        r2 = self.check("default", "client-003")
        assert r2["remaining"] < r1["remaining"]

    def test_auth_token_limit_is_10(self):
        assert self.LIMITS["auth_token"]["requests"] == 10

    def test_face_verify_limit_is_30(self):
        assert self.LIMITS["face_verify"]["requests"] == 30

    def test_nid_scan_limit_is_60(self):
        assert self.LIMITS["nid_scan"]["requests"] == 60

    def test_limit_exceeded_after_max(self):
        limit = self.LIMITS["auth_token"]["requests"]
        for _ in range(limit):
            self.check("auth_token", "client-004")
        r = self.check("auth_token", "client-004")
        assert r["allowed"] is False

    def test_different_clients_independent(self):
        for _ in range(5):
            self.check("default", "client-A")
        r = self.check("default", "client-B")
        assert r["count"] == 1

    def test_result_has_reset_at(self):
        r = self.check("default", "client-005")
        assert "reset_at" in r


class TestDataResidency:
    def setup_method(self):
        from app.services.gateway_service import (
            check_data_residency, add_whitelisted_domain,
            WHITELISTED_DOMAINS, PII_FIELDS,
        )
        self.check    = check_data_residency
        self.whitelist = add_whitelisted_domain
        self.domains  = WHITELISTED_DOMAINS
        self.PII      = PII_FIELDS

    def test_whitelisted_domain_with_pii_allowed(self):
        r = self.check("nid.ec.gov.bd", {"nid_number": "1234567890123"})
        assert r["allowed"] is True

    def test_non_whitelisted_domain_with_pii_blocked(self):
        r = self.check("foreign-api.example.com", {"nid_number": "1234567890123"})
        assert r["allowed"] is False
        assert r["reason"] == "DATA_RESIDENCY_VIOLATION"

    def test_non_whitelisted_domain_no_pii_allowed(self):
        r = self.check("external-api.example.com", {"product_type": "INSURANCE"})
        assert r["allowed"] is True

    def test_pii_fields_identified(self):
        r = self.check("foreign-api.example.com", {"nid_number": "123", "mobile": "+880"})
        if not r["allowed"]:
            assert len(r["pii_fields_found"]) > 0

    def test_bfiu_ref_in_result(self):
        r = self.check("nid.ec.gov.bd", {})
        assert "23" in r["bfiu_ref"]

    def test_add_domain_to_whitelist(self):
        r = self.whitelist("approved-partner.bd")
        assert "approved-partner.bd" in self.domains

    def test_ec_gov_bd_is_whitelisted(self):
        assert "nid.ec.gov.bd" in self.domains

    def test_porichoy_is_whitelisted(self):
        assert "api.porichoy.gov.bd" in self.domains

    def test_pii_fields_include_nid(self):
        assert "nid_number" in self.PII

    def test_pii_fields_include_biometric(self):
        assert "fingerprint_b64" in self.PII


class TestWebhookEngine:
    def setup_method(self):
        from app.services.gateway_service import (
            register_webhook, dispatch_webhook, get_webhooks,
            get_webhook_delivery_log, verify_webhook_signature,
            reset_webhooks, WEBHOOK_EVENTS,
        )
        self.register  = register_webhook
        self.dispatch  = dispatch_webhook
        self.get       = get_webhooks
        self.log       = get_webhook_delivery_log
        self.verify    = verify_webhook_signature
        self.reset     = reset_webhooks
        self.EVENTS    = WEBHOOK_EVENTS
        self.reset()

    def test_register_returns_webhook_id(self):
        r = self.register("inst-001", "https://inst.example.com/hook", ["onboarding.completed"])
        assert r["success"] is True
        assert "webhook_id" in r

    def test_register_invalid_event_fails(self):
        r = self.register("inst-001", "https://example.com/hook", ["invalid.event"])
        assert r["success"] is False

    def test_register_returns_secret(self):
        r = self.register("inst-001", "https://example.com/hook", ["onboarding.completed"])
        assert "secret" in r
        assert len(r["secret"]) > 10

    def test_dispatch_delivers_to_registered(self):
        self.register("inst-002", "https://example.com/hook", ["face_verify.matched"])
        results = self.dispatch("inst-002", "face_verify.matched", {"session_id": "s-001"})
        assert len(results) == 1

    def test_dispatch_only_matching_events(self):
        self.register("inst-003", "https://example.com/hook", ["onboarding.completed"])
        results = self.dispatch("inst-003", "face_verify.matched", {})
        assert len(results) == 0

    def test_dispatch_creates_delivery_log(self):
        self.register("inst-004", "https://example.com/hook", ["screening.blocked"])
        self.dispatch("inst-004", "screening.blocked", {"name": "TEST"})
        log = self.log("inst-004")
        assert len(log) == 1

    def test_delivery_has_signature(self):
        self.register("inst-005", "https://example.com/hook", ["edd.triggered"])
        results = self.dispatch("inst-005", "edd.triggered", {"profile_id": "p-001"})
        assert "signature" in results[0]

    def test_verify_signature_valid(self):
        r       = self.register("inst-006", "https://example.com/hook", ["account.closed"])
        secret  = r["secret"]
        payload = {"profile_id": "p-001"}
        results = self.dispatch("inst-006", "account.closed", payload)
        sig     = results[0]["signature"]
        assert self.verify(payload, secret, sig) is True

    def test_verify_signature_invalid(self):
        assert self.verify({"data": "x"}, "wrong-secret", "invalidsig") is False

    def test_webhook_events_count(self):
        assert len(self.EVENTS) >= 10

    def test_get_webhooks_list(self):
        self.register("inst-007", "https://example.com/hook", ["onboarding.failed"])
        hooks = self.get("inst-007")
        assert len(hooks) == 1
        assert "secret" not in hooks[0]


class TestGatewayAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        self.client.post("/api/v1/auth/register", json={
            "email": "admin_gw@demo.com", "phone": "+8801712345678",
            "full_name": "Gateway Admin", "role": "ADMIN", "password": "admin1234",
        })
        import pyotp as _p12; _SS12 = "JBSWY3DPEHPK3PXP"
        from app.api.v1.routes.auth import _demo_users
        _uu12 = next((x for x in _demo_users if x.email == "admin_gw@demo.com"), None)
        if _uu12 is None:
            try:
                from app.db.database import SessionLocal
                from app.db.models import User as UserModel
                _db = SessionLocal()
                _uu12 = _db.query(UserModel).filter_by(email="admin_gw@demo.com").first()
                _db.close()
                if _uu12:
                    _db2 = SessionLocal()
                    _db2.query(UserModel).filter_by(email="admin_gw@demo.com").update(
                        {"totp_secret": _SS12, "totp_enabled": True})
                    _db2.commit(); _db2.close()
                    _uu12.totp_secret = _SS12; _uu12.totp_enabled = True
                    _demo_users.append(_uu12)
            except Exception as e:
                print(f"[m12 setup] DB fallback: {e}")
        if _uu12 and not _uu12.totp_enabled: _uu12.totp_secret = _SS12; _uu12.totp_enabled = True
        r = self.client.post("/api/v1/auth/token", json={
            "email": "admin_gw@demo.com", "password": "admin1234",
            "totp_code": _p12.TOTP(_SS12).now(),
        })
        self.token   = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        from app.services.gateway_service import reset_webhooks, reset_rate_limits
        reset_webhooks()
        reset_rate_limits()

    def test_health_check_no_auth(self):
        r = self.client.get("/api/v1/gateway/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_version_endpoint(self):
        r = self.client.get("/api/v1/gateway/version")
        assert r.status_code == 200
        assert "current_version" in r.json()

    def test_register_webhook(self):
        r = self.client.post("/api/v1/gateway/webhook/register", json={
            "institution_id": "inst-001",
            "url":            "https://example.com/hook",
            "events":         ["onboarding.completed"],
        }, headers=self.headers)
        assert r.status_code == 201
        assert "webhook_id" in r.json()

    def test_register_invalid_event_422(self):
        r = self.client.post("/api/v1/gateway/webhook/register", json={
            "institution_id": "inst-001",
            "url":            "https://example.com/hook",
            "events":         ["invalid.event"],
        }, headers=self.headers)
        assert r.status_code == 422

    def test_webhook_list(self):
        self.client.post("/api/v1/gateway/webhook/register", json={
            "institution_id": "inst-002",
            "url":            "https://example.com/hook",
            "events":         ["face_verify.matched"],
        }, headers=self.headers)
        r = self.client.get("/api/v1/gateway/webhook/list",
                            params={"institution_id": "inst-002"},
                            headers=self.headers)
        assert r.status_code == 200
        assert len(r.json()["webhooks"]) == 1

    def test_dispatch_webhook(self):
        self.client.post("/api/v1/gateway/webhook/register", json={
            "institution_id": "inst-003",
            "url":            "https://example.com/hook",
            "events":         ["screening.blocked"],
        }, headers=self.headers)
        r = self.client.post("/api/v1/gateway/webhook/dispatch", json={
            "institution_id": "inst-003",
            "event":          "screening.blocked",
            "payload":        {"name": "TEST"},
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["dispatched"] == 1

    def test_residency_check_blocked(self):
        r = self.client.post("/api/v1/gateway/residency/check", json={
            "destination_domain": "foreign-cloud.example.com",
            "payload":            {"nid_number": "1234567890123"},
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["allowed"] is False

    def test_residency_check_allowed(self):
        r = self.client.post("/api/v1/gateway/residency/check", json={
            "destination_domain": "nid.ec.gov.bd",
            "payload":            {"nid_number": "1234567890123"},
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["allowed"] is True

    def test_rate_limits_endpoint(self):
        r = self.client.get("/api/v1/gateway/rate-limits", headers=self.headers)
        assert r.status_code == 200
        assert "auth_token" in r.json()["rate_limits"]

    def test_rate_limit_check(self):
        r = self.client.post("/api/v1/gateway/rate-limits/check", json={
            "endpoint":   "face_verify",
            "client_key": "test-client",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["allowed"] is True

    def test_openapi_summary(self):
        r = self.client.get("/api/v1/gateway/openapi-summary", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data
        assert data["bfiu_compliant"] is True

    def test_webhook_events_list(self):
        r = self.client.get("/api/v1/gateway/webhook/events", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 10

    def test_health_check_has_version(self):
        r = self.client.get("/api/v1/gateway/health")
        assert "version" in r.json()

    def test_unauthenticated_protected_fails(self):
        r = self.client.get("/api/v1/gateway/rate-limits")
        assert r.status_code == 403
