"""
test_admin.py — M13 Admin Console API
Tests: Institution Mgmt, User Mgmt, Threshold Editor,
       Webhook Mgmt, System Health, Audit Log Viewer
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ── helpers ────────────────────────────────────────────────────────────────
def make_institution(name="Test Bank", code="TB"):
    return client.post("/api/v1/admin/institutions", json={
        "name": name, "short_code": code,
        "ip_whitelist": ["192.168.1.1"], "active": True,
    })

def make_user(role="agent", inst_id="inst_01"):
    return client.post("/api/v1/admin/users", json={
        "username": f"user_{role}", "email": f"{role}@test.com",
        "role": role, "institution_id": inst_id, "active": True,
    })

def make_webhook():
    return client.post("/api/v1/admin/webhooks", json={
        "url": "https://hook.example.com/ekyc",
        "events": ["kyc.onboarding.completed", "risk.edd.triggered"],
        "secret": "s3cr3t", "active": True,
    })

# ══════════════════════════════════════════════════════════════════════════
# 1. Institution Management (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestInstitutions:
    def test_list_institutions_empty(self):
        r = client.get("/api/v1/admin/institutions")
        assert r.status_code == 200
        assert "institutions" in r.json()

    def test_create_institution_201(self):
        r = make_institution("First Insurance Ltd", "FIL")
        assert r.status_code == 201
        d = r.json()["institution"]
        assert d["name"] == "First Insurance Ltd"
        assert d["short_code"] == "FIL"
        assert d["schema_name"] == "tenant_fil"
        assert "id" in d

    def test_create_institution_auto_schema(self):
        r = make_institution("Alpha CMI", "ACMI")
        assert r.status_code == 201
        assert r.json()["institution"]["schema_name"] == "tenant_acmi"

    def test_create_institution_custom_schema(self):
        r = client.post("/api/v1/admin/institutions", json={
            "name": "Custom Corp", "short_code": "CC",
            "schema_name": "my_custom_schema", "active": True,
        })
        assert r.status_code == 201
        assert r.json()["institution"]["schema_name"] == "my_custom_schema"

    def test_list_institutions_after_create(self):
        make_institution("List Test", "LT")
        r = client.get("/api/v1/admin/institutions")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_update_institution(self):
        r = make_institution("Old Name", "ON")
        iid = r.json()["institution"]["id"]
        u = client.put(f"/api/v1/admin/institutions/{iid}", json={
            "name": "New Name", "short_code": "NN",
            "ip_whitelist": ["10.0.0.1"], "active": False,
        })
        assert u.status_code == 200
        assert u.json()["institution"]["name"] == "New Name"
        assert u.json()["institution"]["active"] is False

    def test_delete_institution(self):
        r = make_institution("To Delete", "TD")
        iid = r.json()["institution"]["id"]
        d = client.delete(f"/api/v1/admin/institutions/{iid}")
        assert d.status_code == 200
        assert d.json()["deleted"] == iid
        # 404 on second delete
        assert client.delete(f"/api/v1/admin/institutions/{iid}").status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 2. User Management (9 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestUsers:
    def test_list_users_empty_or_ok(self):
        r = client.get("/api/v1/admin/users")
        assert r.status_code == 200
        assert "users" in r.json()

    @pytest.mark.parametrize("role", ["admin", "checker", "maker", "agent", "auditor"])
    def test_create_user_all_roles(self, role):
        r = client.post("/api/v1/admin/users", json={
            "username": f"u_{role}", "email": f"{role}@x.com",
            "role": role, "institution_id": "inst_1", "active": True,
        })
        assert r.status_code == 201
        assert r.json()["user"]["role"] == role

    def test_create_user_invalid_role(self):
        r = client.post("/api/v1/admin/users", json={
            "username": "bad", "email": "bad@x.com",
            "role": "superuser", "institution_id": "inst_1",
        })
        assert r.status_code == 400

    def test_filter_users_by_role(self):
        client.post("/api/v1/admin/users", json={
            "username": "filterable_agent", "email": "fa@x.com",
            "role": "agent", "institution_id": "i1",
        })
        r = client.get("/api/v1/admin/users?role=agent")
        assert r.status_code == 200
        assert all(u["role"] == "agent" for u in r.json()["users"])

    def test_deactivate_user(self):
        r = make_user("maker")
        uid = r.json()["user"]["id"]
        d = client.put(f"/api/v1/admin/users/{uid}/activate?active=false")
        assert d.status_code == 200
        assert d.json()["user"]["active"] is False

    def test_reactivate_user(self):
        r = make_user("checker")
        uid = r.json()["user"]["id"]
        client.put(f"/api/v1/admin/users/{uid}/activate?active=false")
        a = client.put(f"/api/v1/admin/users/{uid}/activate?active=true")
        assert a.status_code == 200
        assert a.json()["user"]["active"] is True

    def test_delete_user(self):
        r = make_user("auditor")
        uid = r.json()["user"]["id"]
        d = client.delete(f"/api/v1/admin/users/{uid}")
        assert d.status_code == 200
        assert d.json()["deleted"] == uid

    def test_delete_nonexistent_user(self):
        assert client.delete("/api/v1/admin/users/nonexistent").status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 3. Threshold Editor (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestThresholds:
    def test_get_thresholds_returns_all_keys(self):
        r = client.get("/api/v1/admin/thresholds")
        assert r.status_code == 200
        t = r.json()["thresholds"]
        for key in ["simplified_max_amount", "regular_min_amount", "edd_risk_score",
                    "high_risk_review_years", "med_risk_review_years", "low_risk_review_years",
                    "max_nid_attempts", "max_sessions"]:
            assert key in t, f"Missing key: {key}"

    def test_update_threshold_edd_score(self):
        r = client.put("/api/v1/admin/thresholds", json={"key": "edd_risk_score", "value": 20})
        assert r.status_code == 200
        assert r.json()["new_value"] == 20

    def test_update_threshold_simplified_amount(self):
        r = client.put("/api/v1/admin/thresholds", json={"key": "simplified_max_amount", "value": 750000})
        assert r.status_code == 200
        assert r.json()["new_value"] == 750000
        assert r.json()["old_value"] is not None

    def test_update_threshold_max_sessions(self):
        r = client.put("/api/v1/admin/thresholds", json={"key": "max_sessions", "value": 3})
        assert r.status_code == 200
        assert r.json()["new_value"] == 3

    def test_update_unknown_threshold_400(self):
        r = client.put("/api/v1/admin/thresholds", json={"key": "invalid_key", "value": 99})
        assert r.status_code == 400

    def test_reset_thresholds_restores_defaults(self):
        client.put("/api/v1/admin/thresholds", json={"key": "edd_risk_score", "value": 99})
        r = client.post("/api/v1/admin/thresholds/reset")
        assert r.status_code == 200
        assert r.json()["thresholds"]["edd_risk_score"] == 15

    def test_threshold_value_reflected_in_get(self):
        client.put("/api/v1/admin/thresholds", json={"key": "max_nid_attempts", "value": 5})
        r = client.get("/api/v1/admin/thresholds")
        assert r.json()["thresholds"]["max_nid_attempts"] == 5

# ══════════════════════════════════════════════════════════════════════════
# 4. Webhook Management (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestWebhooks:
    def test_list_webhooks_empty_or_ok(self):
        r = client.get("/api/v1/admin/webhooks")
        assert r.status_code == 200
        assert "webhooks" in r.json()

    def test_create_webhook_201(self):
        r = make_webhook()
        assert r.status_code == 201
        w = r.json()["webhook"]
        assert w["url"] == "https://hook.example.com/ekyc"
        assert "kyc.onboarding.completed" in w["events"]
        assert "id" in w

    def test_create_webhook_stores_events(self):
        r = client.post("/api/v1/admin/webhooks", json={
            "url": "https://another.com/wh",
            "events": ["screening.sanctions.hit", "auth.login.failed"],
        })
        assert r.status_code == 201
        assert len(r.json()["webhook"]["events"]) == 2

    def test_list_webhooks_after_create(self):
        make_webhook()
        r = client.get("/api/v1/admin/webhooks")
        assert r.json()["total"] >= 1

    def test_delete_webhook(self):
        r = make_webhook()
        wid = r.json()["webhook"]["id"]
        d = client.delete(f"/api/v1/admin/webhooks/{wid}")
        assert d.status_code == 200
        assert d.json()["deleted"] == wid

    def test_delete_nonexistent_webhook_404(self):
        assert client.delete("/api/v1/admin/webhooks/ghost").status_code == 404

    def test_webhook_logs_endpoint(self):
        r = client.get("/api/v1/admin/webhooks/logs")
        assert r.status_code == 200
        assert "logs" in r.json()

# ══════════════════════════════════════════════════════════════════════════
# 5. System Health (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/api/v1/admin/health")
        assert r.status_code == 200

    def test_health_status_healthy(self):
        r = client.get("/api/v1/admin/health")
        assert r.json()["status"] == "healthy"

    def test_health_has_modules(self):
        r = client.get("/api/v1/admin/health")
        modules = r.json()["modules"]
        for m in ["auth", "nid", "face_verify", "risk", "screening"]:
            assert m in modules
            assert modules[m] == "ok"

    def test_health_has_rate_limits(self):
        r = client.get("/api/v1/admin/health")
        rl = r.json()["rate_limits"]
        assert "nid_attempts_per_session" in rl
        assert "max_concurrent_sessions" in rl

    def test_health_has_whitelisted_domains(self):
        r = client.get("/api/v1/admin/health")
        domains = r.json()["whitelisted_domains"]
        assert isinstance(domains, list)
        assert len(domains) > 0
        assert any("gov.bd" in d for d in domains)

# ══════════════════════════════════════════════════════════════════════════
# 6. Audit Log Viewer (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAuditLogs:
    def test_audit_logs_returns_200(self):
        r = client.get("/api/v1/admin/audit-logs")
        assert r.status_code == 200

    def test_audit_logs_has_entries(self):
        r = client.get("/api/v1/admin/audit-logs")
        d = r.json()
        assert "logs" in d
        assert "total" in d
        assert d["total"] > 0

    def test_audit_logs_filter_by_severity_warning(self):
        r = client.get("/api/v1/admin/audit-logs?severity=warning")
        assert r.status_code == 200
        for log in r.json()["logs"]:
            assert log["severity"] == "warning"

    def test_audit_logs_filter_by_event_type(self):
        r = client.get("/api/v1/admin/audit-logs?event_type=auth")
        assert r.status_code == 200
        for log in r.json()["logs"]:
            assert "auth" in log["event_type"]

    def test_audit_logs_export_json(self):
        r = client.get("/api/v1/admin/audit-logs/export?fmt=json")
        assert r.status_code == 200
        d = r.json()
        assert d["format"] == "json"
        assert isinstance(d["data"], list)

    def test_audit_logs_export_csv(self):
        r = client.get("/api/v1/admin/audit-logs/export?fmt=csv")
        assert r.status_code == 200
        d = r.json()
        assert d["format"] == "csv"
        assert "id,event_type" in d["data"]
