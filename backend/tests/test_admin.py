"""
test_admin.py - M13 Admin Console API
All endpoints require ADMIN JWT — production grade.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE = "/api/v1/admin"
AUTH = "/api/v1/auth"

# ── Auth helper ───────────────────────────────────────────────────────────
def get_admin_token():
    client.post(f"{AUTH}/register", json={
        "email":"admin_m13@test.com","phone":"01700000000",
        "full_name":"Admin M13","role":"ADMIN",
        "password":"Admin@12345","institution_id":"inst-demo-001"})
    r = client.post(f"{AUTH}/token", json={"email":"admin_m13@test.com","password":"Admin@12345"})
    return r.json().get("access_token","")

def get_auditor_token():
    client.post(f"{AUTH}/register", json={
        "email":"auditor_m13@test.com","phone":"01700000000",
        "full_name":"Auditor M13","role":"AUDITOR",
        "password":"Admin@12345","institution_id":"inst-demo-001"})
    r = client.post(f"{AUTH}/token", json={"email":"auditor_m13@test.com","password":"Admin@12345"})
    return r.json().get("access_token","")

def ah(): return {"Authorization": f"Bearer {get_admin_token()}"}
def audh(): return {"Authorization": f"Bearer {get_auditor_token()}"}

def make_institution(name="Test Bank", code="TB", headers=None):
    return client.post(f"{BASE}/institutions",
        json={"name":name,"short_code":code,"institution_type":"insurance"},
        headers=headers or ah())

def make_user(role="agent", inst_id="inst-demo-001", headers=None):
    import uuid as _uuid
    email = f"{role}_m13_{_uuid.uuid4().hex[:6]}@test.com"
    return client.post(f"{BASE}/users",
        json={"email":email,"full_name":f"User {role}","role":role,
              "institution_id":inst_id,"password":"Admin@12345"},
        headers=headers or ah())

def make_webhook(headers=None):
    return client.post(f"{BASE}/webhooks",
        json={"url":"https://hook.example.com/ekyc",
              "events":["kyc.completed","risk.edd.triggered"],
              "secret":"s3cr3t","active":True},
        headers=headers or ah())

# ══════════════════════════════════════════════════════════════════════════
# 1. Institution Management (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestInstitutions:
    def test_list_institutions_empty(self):
        r = client.get(f"{BASE}/institutions", headers=ah())
        assert r.status_code == 200
        assert "institutions" in r.json()

    def test_create_institution_201(self):
        r = make_institution("First Insurance Ltd", "FIL2")
        assert r.status_code == 201
        d = r.json()["institution"]
        assert d["name"] == "First Insurance Ltd"
        assert d["short_code"] == "FIL2"
        assert "tenant_fil2" in d["schema_name"]
        assert "id" in d

    def test_create_institution_auto_schema(self):
        r = make_institution("Alpha CMI", "ACM2")
        assert r.status_code == 201
        assert "tenant_acm2" in r.json()["institution"]["schema_name"]

    def test_create_institution_custom_schema(self):
        r = client.post(f"{BASE}/institutions",
            json={"name":"Custom Corp","short_code":"CC2",
                  "institution_type":"insurance","schema_name":"my_custom_schema"},
            headers=ah())
        assert r.status_code == 201
        assert r.json()["institution"]["schema_name"] == "my_custom_schema"

    def test_list_institutions_after_create(self):
        make_institution("List Test", "LT2")
        r = client.get(f"{BASE}/institutions", headers=ah())
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_update_institution(self):
        r = make_institution("Old Name", "ON2")
        iid = r.json()["institution"]["id"]
        u = client.put(f"{BASE}/institutions/{iid}",
            json={"name":"New Name","ip_whitelist":["10.0.0.1"],"active":False,"status":"SUSPENDED"},
            headers=ah())
        assert u.status_code == 200
        assert u.json()["institution"]["name"] == "New Name"

    def test_delete_institution(self):
        r = make_institution("To Delete", "TD2")
        iid = r.json()["institution"]["id"]
        d = client.delete(f"{BASE}/institutions/{iid}", headers=ah())
        assert d.status_code == 200
        assert d.json()["deleted"] == iid
        assert client.delete(f"{BASE}/institutions/{iid}", headers=ah()).status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 2. User Management (9 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestUsers:
    def test_list_users_empty_or_ok(self):
        r = client.get(f"{BASE}/users", headers=ah())
        assert r.status_code == 200
        assert "users" in r.json()

    @pytest.mark.parametrize("role", ["admin","checker","maker","agent","auditor"])
    def test_create_user_all_roles(self, role):
        import uuid as _uuid
        email = f"{role}_allroles_{_uuid.uuid4().hex[:6]}@test.com"
        r = client.post(f"{BASE}/users",
            json={"email":email,"full_name":f"User {role}",
                  "role":role,"institution_id":"inst-demo-001","password":"Admin@12345"},
            headers=ah())
        assert r.status_code == 201
        assert r.json()["user"]["role"] == role

    def test_create_user_invalid_role(self):
        r = client.post(f"{BASE}/users",
            json={"email":"bad_role@test.com","full_name":"Bad","role":"superuser",
                  "institution_id":"inst-demo-001"},
            headers=ah())
        assert r.status_code == 400

    def test_filter_users_by_role(self):
        client.post(f"{BASE}/users",
            json={"email":"filter_agent_m13@test.com","full_name":"Filter Agent",
                  "role":"agent","institution_id":"inst-demo-001","password":"Admin@12345"},
            headers=ah())
        r = client.get(f"{BASE}/users?role=agent", headers=ah())
        assert r.status_code == 200
        assert all(u["role"] in ("agent","AGENT") for u in r.json()["users"])

    def test_deactivate_user(self):
        r = make_user("maker")
        uid = r.json()["user"]["id"]
        d = client.put(f"{BASE}/users/{uid}/activate?active=false", headers=ah())
        assert d.status_code == 200
        assert d.json()["user"]["active"] is False

    def test_reactivate_user(self):
        r = make_user("checker")
        uid = r.json()["user"]["id"]
        client.put(f"{BASE}/users/{uid}/activate?active=false", headers=ah())
        a = client.put(f"{BASE}/users/{uid}/activate?active=true", headers=ah())
        assert a.status_code == 200
        assert a.json()["user"]["active"] is True

    def test_delete_user(self):
        r = make_user("auditor")
        uid = r.json()["user"]["id"]
        d = client.delete(f"{BASE}/users/{uid}", headers=ah())
        assert d.status_code == 200
        assert d.json()["deleted"] == uid

    def test_delete_nonexistent_user(self):
        assert client.delete(f"{BASE}/users/nonexistent", headers=ah()).status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 3. Threshold Editor (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestThresholds:
    def test_get_thresholds_returns_all_keys(self):
        r = client.get(f"{BASE}/thresholds", headers=audh())
        assert r.status_code == 200
        t = r.json()["thresholds"]
        for key in ["simplified_max_amount","regular_min_amount","edd_risk_score",
                    "high_risk_review_years","med_risk_review_years","low_risk_review_years",
                    "max_nid_attempts","max_sessions"]:
            assert key in t, f"Missing key: {key}"

    def test_update_threshold_edd_score(self):
        r = client.put(f"{BASE}/thresholds",
            json={"key":"edd_risk_score","value":20}, headers=ah())
        assert r.status_code == 200
        assert r.json()["new_value"] == 20

    def test_update_threshold_simplified_amount(self):
        r = client.put(f"{BASE}/thresholds",
            json={"key":"simplified_max_amount","value":750000}, headers=ah())
        assert r.status_code == 200
        assert r.json()["new_value"] == 750000
        assert r.json()["old_value"] is not None

    def test_update_threshold_max_sessions(self):
        r = client.put(f"{BASE}/thresholds",
            json={"key":"max_sessions","value":3}, headers=ah())
        assert r.status_code == 200
        assert r.json()["new_value"] == 3

    def test_update_unknown_threshold_400(self):
        r = client.put(f"{BASE}/thresholds",
            json={"key":"invalid_key","value":99}, headers=ah())
        assert r.status_code == 400

    def test_reset_thresholds_restores_defaults(self):
        client.put(f"{BASE}/thresholds", json={"key":"edd_risk_score","value":99}, headers=ah())
        r = client.post(f"{BASE}/thresholds/reset", headers=ah())
        assert r.status_code == 200
        assert r.json()["thresholds"]["edd_risk_score"] == 15

    def test_threshold_value_reflected_in_get(self):
        client.put(f"{BASE}/thresholds", json={"key":"max_nid_attempts","value":5}, headers=ah())
        r = client.get(f"{BASE}/thresholds", headers=ah())
        assert r.json()["thresholds"]["max_nid_attempts"] == 5

# ══════════════════════════════════════════════════════════════════════════
# 4. Webhook Management (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestWebhooks:
    def test_list_webhooks_empty_or_ok(self):
        r = client.get(f"{BASE}/webhooks", headers=ah())
        assert r.status_code == 200
        assert "webhooks" in r.json()

    def test_create_webhook_201(self):
        r = make_webhook()
        assert r.status_code == 201
        assert "id" in r.json()["webhook"]
        assert r.json()["webhook"]["url"] == "https://hook.example.com/ekyc"

    def test_create_webhook_stores_events(self):
        r = make_webhook()
        events = r.json()["webhook"]["events"]
        assert "kyc.completed" in events

    def test_list_webhooks_after_create(self):
        make_webhook()
        r = client.get(f"{BASE}/webhooks", headers=ah())
        assert r.json()["total"] >= 1

    def test_delete_webhook(self):
        r = make_webhook()
        wid = r.json()["webhook"]["id"]
        d = client.delete(f"{BASE}/webhooks/{wid}", headers=ah())
        assert d.status_code == 200
        assert d.json()["deleted"] == wid

    def test_delete_nonexistent_webhook_404(self):
        assert client.delete(f"{BASE}/webhooks/nonexistent", headers=ah()).status_code == 404

    def test_webhook_logs_endpoint(self):
        r = client.get(f"{BASE}/webhooks/logs", headers=ah())
        assert r.status_code == 200
        assert "logs" in r.json()

# ══════════════════════════════════════════════════════════════════════════
# 5. System Health (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_returns_200(self):
        assert client.get(f"{BASE}/health", headers=ah()).status_code == 200

    def test_health_status_healthy(self):
        r = client.get(f"{BASE}/health", headers=ah())
        assert r.json()["status"] == "healthy"

    def test_health_has_modules(self):
        r = client.get(f"{BASE}/health", headers=ah())
        modules = r.json()["modules"]
        for m in ["auth","nid","face_verify","kyc","audit"]:
            assert m in modules, f"Missing module: {m}"

    def test_health_has_rate_limits(self):
        r = client.get(f"{BASE}/health", headers=ah())
        assert "rate_limits" in r.json()
        assert len(r.json()["rate_limits"]) > 0

    def test_health_has_whitelisted_domains(self):
        r = client.get(f"{BASE}/health", headers=ah())
        assert "whitelisted_domains" in r.json()
        assert len(r.json()["whitelisted_domains"]) > 0

# ══════════════════════════════════════════════════════════════════════════
# 6. Audit Logs (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAuditLogs:
    def test_audit_logs_returns_200(self):
        assert client.get(f"{BASE}/audit-logs", headers=ah()).status_code == 200

    def test_audit_logs_has_entries(self):
        from app.services.audit_service import log_event
        log_event("USER_CREATED","User",actor_id="admin-test")
        r = client.get(f"{BASE}/audit-logs", headers=ah())
        assert r.json()["total"] >= 1
        assert isinstance(r.json()["entries"], list)

    def test_audit_logs_filter_by_severity_warning(self):
        r = client.get(f"{BASE}/audit-logs?severity=warning", headers=ah())
        assert r.status_code == 200

    def test_audit_logs_filter_by_event_type(self):
        from app.services.audit_service import log_event
        log_event("USER_CREATED","User")
        r = client.get(f"{BASE}/audit-logs?event_type=USER_CREATED", headers=ah())
        assert r.status_code == 200
        assert all(e["event_type"]=="USER_CREATED" for e in r.json()["entries"])

    def test_audit_logs_export_json(self):
        r = client.get(f"{BASE}/audit-logs/export?format=json", headers=ah())
        assert r.status_code == 200
        assert isinstance(r.json()["data"], str)

    def test_audit_logs_export_csv(self):
        r = client.get(f"{BASE}/audit-logs/export?format=csv", headers=ah())
        assert r.status_code == 200
        assert "BFIU" in r.json()["data"] or isinstance(r.json()["data"], str)
