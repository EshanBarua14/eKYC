"""
test_m45_rbac.py — M45 RBAC Role-Based Access Control
Full test coverage for all 5 roles: ADMIN, CHECKER, MAKER, AGENT, AUDITOR
Tests: login, portal access, permission enforcement, 2FA enforcement, cross-role blocking
BFIU Circular No. 29 — Section 4.3 Role-Based Access
"""
import pytest
import pyotp
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1"
AUTH   = f"{BASE}/auth"
ADMIN  = f"{BASE}/admin"

TOTP_SECRET = "JBSWY3DPEHPK3PXP"

# ── Demo credentials ──────────────────────────────────────────────────────
DEMO_USERS = {
    "ADMIN":   {"email":"admin@demo.ekyc",   "password":"AdminDemo@2026",   "totp":True },
    "CHECKER": {"email":"checker@demo.ekyc", "password":"DemoChecker@2026", "totp":True },
    "MAKER":   {"email":"maker@demo.ekyc",   "password":"DemoMaker@2026",   "totp":False},
    "AGENT":   {"email":"agent@demo.ekyc",   "password":"DemoAgent@2026",   "totp":False},
    "AUDITOR": {"email":"auditor@demo.ekyc", "password":"DemoAudit@2026",   "totp":False},
}

def get_token(role: str) -> str:
    u = DEMO_USERS[role]
    payload = {"email": u["email"], "password": u["password"]}
    if u["totp"]:
        payload["totp_code"] = pyotp.TOTP(TOTP_SECRET).now()
    r = client.post(f"{AUTH}/token", json=payload)
    assert r.status_code == 200, f"{role} login failed: {r.text}"
    return r.json()["access_token"]

def hdrs(role: str) -> dict:
    return {"Authorization": f"Bearer {get_token(role)}"}

# ══════════════════════════════════════════════════════════════════════════
# 1. Authentication — all roles can login
# ══════════════════════════════════════════════════════════════════════════
class TestRBACLogin:
    def test_admin_login_succeeds(self):
        u = DEMO_USERS["ADMIN"]
        r = client.post(f"{AUTH}/token", json={
            "email": u["email"], "password": u["password"],
            "totp_code": pyotp.TOTP(TOTP_SECRET).now()
        })
        assert r.status_code == 200
        assert r.json()["role"] == "ADMIN"

    def test_checker_login_requires_totp(self):
        u = DEMO_USERS["CHECKER"]
        r = client.post(f"{AUTH}/token", json={"email": u["email"], "password": u["password"]})
        assert r.status_code == 401
        assert "2FA" in r.text or "TOTP" in r.text or "setup" in r.text.lower()

    def test_checker_login_with_totp_succeeds(self):
        u = DEMO_USERS["CHECKER"]
        r = client.post(f"{AUTH}/token", json={
            "email": u["email"], "password": u["password"],
            "totp_code": pyotp.TOTP(TOTP_SECRET).now()
        })
        assert r.status_code == 200
        assert r.json()["role"] == "CHECKER"

    def test_maker_login_no_totp_required(self):
        u = DEMO_USERS["MAKER"]
        r = client.post(f"{AUTH}/token", json={"email": u["email"], "password": u["password"]})
        assert r.status_code == 200
        assert r.json()["role"] == "MAKER"

    def test_agent_login_succeeds(self):
        u = DEMO_USERS["AGENT"]
        r = client.post(f"{AUTH}/token", json={"email": u["email"], "password": u["password"]})
        assert r.status_code == 200
        assert r.json()["role"] == "AGENT"

    def test_auditor_login_succeeds(self):
        u = DEMO_USERS["AUDITOR"]
        r = client.post(f"{AUTH}/token", json={"email": u["email"], "password": u["password"]})
        assert r.status_code == 200
        assert r.json()["role"] == "AUDITOR"

    def test_wrong_password_blocked(self):
        r = client.post(f"{AUTH}/token", json={"email":"agent@demo.ekyc","password":"wrong"})
        assert r.status_code == 401

    def test_unknown_user_blocked(self):
        r = client.post(f"{AUTH}/token", json={"email":"nobody@demo.ekyc","password":"pass"})
        assert r.status_code == 401

    def test_no_token_returns_403(self):
        r = client.get(f"{AUTH}/me")
        assert r.status_code in (401, 403)

    def test_jwt_payload_contains_role(self):
        import base64, json
        token = get_token("AGENT")
        payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        assert payload["role"] == "AGENT"
        assert "user_id" in payload
        assert "exp" in payload

# ══════════════════════════════════════════════════════════════════════════
# 2. ADMIN role — full access
# ══════════════════════════════════════════════════════════════════════════
class TestAdminRole:
    def test_admin_can_list_institutions(self):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs("ADMIN"))
        assert r.status_code == 200
        assert "institutions" in r.json()

    def test_admin_can_list_users(self):
        r = client.get(f"{ADMIN}/users", headers=hdrs("ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_health(self):
        r = client.get(f"{ADMIN}/health", headers=hdrs("ADMIN"))
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_admin_can_view_audit_logs(self):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs("ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_thresholds(self):
        r = client.get(f"{ADMIN}/thresholds", headers=hdrs("ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_webhooks(self):
        r = client.get(f"{ADMIN}/webhooks", headers=hdrs("ADMIN"))
        assert r.status_code == 200

    def test_admin_can_access_me(self):
        r = client.get(f"{AUTH}/me", headers=hdrs("ADMIN"))
        assert r.status_code == 200
        assert r.json()["role"] == "ADMIN"

# ══════════════════════════════════════════════════════════════════════════
# 3. CHECKER role — review access
# ══════════════════════════════════════════════════════════════════════════
class TestCheckerRole:
    def test_checker_can_access_me(self):
        r = client.get(f"{AUTH}/me", headers=hdrs("CHECKER"))
        assert r.status_code == 200
        assert r.json()["role"] == "CHECKER"

    def test_checker_can_view_audit_logs(self):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs("CHECKER"))
        assert r.status_code == 200

    def test_checker_can_view_institutions(self):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs("CHECKER"))
        assert r.status_code == 200

    def test_checker_cannot_create_institution(self):
        r = client.post(f"{ADMIN}/institutions", headers=hdrs("CHECKER"),
                        json={"name":"Hack","short_code":"HCK","institution_type":"bank"})
        assert r.status_code == 403

    def test_checker_cannot_delete_institution(self):
        r = client.delete(f"{ADMIN}/institutions/inst-demo-001", headers=hdrs("CHECKER"))
        assert r.status_code == 403

    def test_checker_cannot_create_user(self):
        r = client.post(f"{ADMIN}/users", headers=hdrs("CHECKER"),
                        json={"email":"x@x.com","full_name":"X","role":"AGENT","phone":"01700000000","password":"Test@1234"})
        assert r.status_code == 403

    def test_checker_cannot_update_thresholds(self):
        r = client.put(f"{ADMIN}/thresholds", headers=hdrs("CHECKER"),
                       json={"key":"edd_risk_score","value":5})
        assert r.status_code == 403

# ══════════════════════════════════════════════════════════════════════════
# 4. MAKER role — onboarding only
# ══════════════════════════════════════════════════════════════════════════
class TestMakerRole:
    def test_maker_can_access_me(self):
        r = client.get(f"{AUTH}/me", headers=hdrs("MAKER"))
        assert r.status_code == 200
        assert r.json()["role"] == "MAKER"

    def test_maker_cannot_access_admin_stats(self):
        r = client.get(f"{ADMIN}/stats", headers=hdrs("MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_list_institutions(self):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs("MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_list_users(self):
        r = client.get(f"{ADMIN}/users", headers=hdrs("MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_view_audit_logs(self):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs("MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_create_institution(self):
        r = client.post(f"{ADMIN}/institutions", headers=hdrs("MAKER"),
                        json={"name":"X","short_code":"XX","institution_type":"bank"})
        assert r.status_code == 403

# ══════════════════════════════════════════════════════════════════════════
# 5. AGENT role — field operations only
# ══════════════════════════════════════════════════════════════════════════
class TestAgentRole:
    def test_agent_can_access_me(self):
        r = client.get(f"{AUTH}/me", headers=hdrs("AGENT"))
        assert r.status_code == 200
        assert r.json()["role"] == "AGENT"

    def test_agent_cannot_access_admin(self):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs("AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_view_users(self):
        r = client.get(f"{ADMIN}/users", headers=hdrs("AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_view_audit_logs(self):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs("AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_view_thresholds(self):
        r = client.get(f"{ADMIN}/thresholds", headers=hdrs("AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_create_user(self):
        r = client.post(f"{ADMIN}/users", headers=hdrs("AGENT"),
                        json={"email":"a@b.com","full_name":"A","role":"AGENT","phone":"01700000000","password":"Test@1234"})
        assert r.status_code == 403

# ══════════════════════════════════════════════════════════════════════════
# 6. AUDITOR role — read-only audit
# ══════════════════════════════════════════════════════════════════════════
class TestAuditorRole:
    def test_auditor_can_access_me(self):
        r = client.get(f"{AUTH}/me", headers=hdrs("AUDITOR"))
        assert r.status_code == 200
        assert r.json()["role"] == "AUDITOR"

    def test_auditor_can_view_audit_logs(self):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs("AUDITOR"))
        assert r.status_code == 200

    def test_auditor_can_view_institutions(self):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs("AUDITOR"))
        assert r.status_code == 200

    def test_auditor_can_view_health(self):
        r = client.get(f"{ADMIN}/health", headers=hdrs("AUDITOR"))
        assert r.status_code == 200

    def test_auditor_cannot_create_institution(self):
        r = client.post(f"{ADMIN}/institutions", headers=hdrs("AUDITOR"),
                        json={"name":"X","short_code":"YY","institution_type":"bank"})
        assert r.status_code == 403

    def test_auditor_cannot_create_user(self):
        r = client.post(f"{ADMIN}/users", headers=hdrs("AUDITOR"),
                        json={"email":"a@b.com","full_name":"A","role":"AGENT","phone":"01700000000","password":"Test@1234"})
        assert r.status_code == 403

    def test_auditor_cannot_update_thresholds(self):
        r = client.put(f"{ADMIN}/thresholds", headers=hdrs("AUDITOR"),
                       json={"key":"edd_risk_score","value":5})
        assert r.status_code == 403

    def test_auditor_cannot_delete_webhook(self):
        r = client.delete(f"{ADMIN}/webhooks/fake-id", headers=hdrs("AUDITOR"))
        assert r.status_code == 403

# ══════════════════════════════════════════════════════════════════════════
# 7. Token security
# ══════════════════════════════════════════════════════════════════════════
class TestTokenSecurity:
    def test_no_token_blocked(self):
        r = client.get(f"{ADMIN}/institutions")
        assert r.status_code in (401, 403)

    def test_tampered_token_blocked(self):
        token = get_token("AGENT")
        parts = token.split(".")
        parts[2] = parts[2][:-4] + "XXXX"
        bad_token = ".".join(parts)
        r = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert r.status_code in (401, 403)

    def test_alg_none_attack_blocked(self):
        import base64, json
        token = get_token("AGENT")
        parts = token.split(".")
        header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
        header["alg"] = "none"
        new_header = base64.urlsafe_b64encode(
            json.dumps(header).encode()).rstrip(b"=").decode()
        bad_token = f"{new_header}.{parts[1]}."
        r = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert r.status_code in (401, 403)

    def test_expired_token_rejected(self):
        from app.core.security import PRIVATE_KEY, ALGORITHM
        from jose import jwt
        from datetime import datetime, timezone, timedelta
        payload = {
            "sub": "inst-demo-001", "user_id": "user-0001",
            "role": "ADMIN", "tenant_schema": "tenant_demo",
            "ip_whitelist": [], "jti": "test-expired",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access"
        }
        expired_token = jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)
        r = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code in (401, 403)

# ══════════════════════════════════════════════════════════════════════════
# 8. 2FA enforcement (BFIU §3.2.5)
# ══════════════════════════════════════════════════════════════════════════
class TestTwoFactorEnforcement:
    def test_admin_without_totp_blocked(self):
        u = DEMO_USERS["ADMIN"]
        r = client.post(f"{AUTH}/token", json={"email":u["email"],"password":u["password"]})
        assert r.status_code == 401
        assert "2FA" in r.text or "TOTP" in r.text or "setup" in r.text.lower()

    def test_checker_without_totp_blocked(self):
        u = DEMO_USERS["CHECKER"]
        r = client.post(f"{AUTH}/token", json={"email":u["email"],"password":u["password"]})
        assert r.status_code == 401

    def test_admin_wrong_totp_blocked(self):
        u = DEMO_USERS["ADMIN"]
        r = client.post(f"{AUTH}/token", json={"email":u["email"],"password":u["password"],"totp_code":"000000"})
        assert r.status_code in (401, 422)

    def test_maker_no_totp_required(self):
        u = DEMO_USERS["MAKER"]
        r = client.post(f"{AUTH}/token", json={"email":u["email"],"password":u["password"]})
        assert r.status_code == 200

    def test_agent_no_totp_required(self):
        u = DEMO_USERS["AGENT"]
        r = client.post(f"{AUTH}/token", json={"email":u["email"],"password":u["password"]})
        assert r.status_code == 200

# ══════════════════════════════════════════════════════════════════════════
# 9. Cross-role privilege escalation prevention
# ══════════════════════════════════════════════════════════════════════════
class TestPrivilegeEscalation:
    def test_agent_cannot_promote_self(self):
        r = client.put(f"{ADMIN}/users/user-0001/role", headers=hdrs("AGENT"),
                       json={"role":"ADMIN"})
        assert r.status_code == 403

    def test_maker_cannot_reset_thresholds(self):
        r = client.post(f"{ADMIN}/thresholds/reset", headers=hdrs("MAKER"))
        assert r.status_code == 403

    def test_auditor_cannot_delete_audit_logs(self):
        r = client.delete(f"{ADMIN}/audit-logs/some-id", headers=hdrs("AUDITOR"))
        assert r.status_code in (403, 404, 405)

    def test_checker_cannot_access_admin_only_endpoints(self):
        r = client.delete(f"{ADMIN}/users/user-0001", headers=hdrs("CHECKER"))
        assert r.status_code == 403

    def test_agent_cannot_view_admin_stats(self):
        r = client.get(f"{ADMIN}/stats", headers=hdrs("AGENT"))
        assert r.status_code == 403
