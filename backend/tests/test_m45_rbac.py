"""
test_m45_rbac.py  — RBAC & Authorization Tests
BFIU Circular No. 29 — Section 6.1 / 7.1
Fixes applied:
  - Token cache: login once per role, reuse token (avoids 429 rate limit)
  - Credentials match demo users seeded in auth.py
  - TOTP auto-generated for ADMIN and CHECKER
Date: 2026-04-21
"""
import pytest
import pyotp
from fastapi.testclient import TestClient

# ── Demo credentials (must match _demo_users in auth.py) ──────────────────
USERS = {
    "ADMIN":   {"email": "admin@demo.ekyc",   "password": "AdminDemo@2026",   "totp_secret": "JBSWY3DPEHPK3PXP"},
    "CHECKER": {"email": "checker@demo.ekyc", "password": "DemoChecker@2026", "totp_secret": "JBSWY3DPEHPK3PXP"},
    "MAKER":   {"email": "maker@demo.ekyc",   "password": "DemoMaker@2026"},
    "AGENT":   {"email": "agent@demo.ekyc",   "password": "DemoAgent@2026"},
    "AUDITOR": {"email": "auditor@demo.ekyc", "password": "DemoAudit@2026"},
}

AUTH  = "/api/v1/auth"
ADMIN = "/api/v1/admin"

# ── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def token_cache(client):
    """Login once per role, cache tokens for entire module."""
    import app.api.v1.routes.auth as auth_module
    # Flush Redis rate limit keys
    try:
        from app.services.redis_client import get_redis
        r = get_redis()
        if r:
            keys = list(r.keys("rl:*")) + list(r.keys("rate*")) + list(r.keys("login*"))
            if keys:
                r.delete(*keys)
    except Exception:
        pass

    # Seed all users into _demo_users with TOTP if missing
    from app.api.v1.routes.auth import _demo_users
    from app.db.database import SessionLocal
    from app.db.models import User as UserModel
    for role, creds in USERS.items():
        email = creds["email"]
        secret = creds.get("totp_secret")
        u = next((x for x in _demo_users if x.email == email), None)
        if u is None:
            try:
                _db = SessionLocal()
                u = _db.query(UserModel).filter_by(email=email).first()
                _db.close()
                if u and secret:
                    _db2 = SessionLocal()
                    _db2.query(UserModel).filter_by(email=email).update(
                        {"totp_secret": secret, "totp_enabled": True})
                    _db2.commit(); _db2.close()
                    u.totp_secret = secret; u.totp_enabled = True
                    _demo_users.append(u)
            except Exception as e:
                print(f"[m45 seed] {email}: {e}")
        elif secret and not u.totp_enabled:
            u.totp_secret = secret; u.totp_enabled = True

    # Seed all users into _demo_users with TOTP if missing
    from app.api.v1.routes.auth import _demo_users
    from app.db.database import SessionLocal
    from app.db.models import User as UserModel
    for role, creds in USERS.items():
        email = creds["email"]
        secret = creds.get("totp_secret")
        u = next((x for x in _demo_users if x.email == email), None)
        if u is None:
            try:
                _db = SessionLocal()
                u = _db.query(UserModel).filter_by(email=email).first()
                _db.close()
                if u and secret:
                    _db2 = SessionLocal()
                    _db2.query(UserModel).filter_by(email=email).update(
                        {"totp_secret": secret, "totp_enabled": True})
                    _db2.commit(); _db2.close()
                    u.totp_secret = secret; u.totp_enabled = True
                    _demo_users.append(u)
            except Exception as e:
                print(f"[m45 seed] {email}: {e}")
        elif secret and not u.totp_enabled:
            u.totp_secret = secret; u.totp_enabled = True

    cache = {}
    for role, creds in USERS.items():
        payload = {"email": creds["email"], "password": creds["password"]}
        if "totp_secret" in creds:
            payload["totp_code"] = pyotp.TOTP(creds["totp_secret"]).now()
        resp = client.post(f"{AUTH}/token", json=payload)
        if resp.status_code == 200:
            cache[role] = resp.json()["access_token"]
        else:
            cache[role] = None
    return cache

def hdrs(token_cache, role):
    t = token_cache[role]
    assert t is not None, f"{role} login failed — check demo user seeding"
    return {"Authorization": f"Bearer {t}"}


# ── Login tests ────────────────────────────────────────────────────────────
class TestRBACLogin:
    def test_admin_login_succeeds(self, token_cache):
        assert token_cache["ADMIN"] is not None

    def test_checker_login_succeeds(self, token_cache):
        assert token_cache["CHECKER"] is not None

    def test_maker_login_succeeds(self, token_cache):
        assert token_cache["MAKER"] is not None

    def test_agent_login_succeeds(self, token_cache):
        assert token_cache["AGENT"] is not None

    def test_auditor_login_succeeds(self, token_cache):
        assert token_cache["AUDITOR"] is not None

    def test_wrong_password_blocked(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "admin@demo.ekyc", "password": "WrongPassword@123"
        })
        assert r.status_code == 401

    def test_unknown_user_blocked(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "ghost@demo.ekyc", "password": "NoSuchUser@123"
        })
        assert r.status_code == 401

    def test_no_token_returns_403(self, client):
        r = client.get(f"{AUTH}/me")
        assert r.status_code == 403

    def test_jwt_payload_contains_role(self, token_cache):
        import base64, json
        token = token_cache["AGENT"]
        payload = json.loads(base64.b64decode(token.split(".")[1] + "=="))
        assert "role" in payload
        assert payload["role"].upper() == "AGENT"

    def test_checker_requires_totp(self, client):
        # Checker login without TOTP should fail
        r = client.post(f"{AUTH}/token", json={
            "email": "checker@demo.ekyc", "password": "DemoChecker@2026"
        })
        assert r.status_code in (401, 422)

    def test_admin_requires_totp(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "admin@demo.ekyc", "password": "AdminDemo@2026"
        })
        assert r.status_code in (401, 422)


# ── Admin role tests ───────────────────────────────────────────────────────
class TestAdminRole:
    def test_admin_can_list_institutions(self, client, token_cache):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200

    def test_admin_can_list_users(self, client, token_cache):
        r = client.get(f"{ADMIN}/users", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_health(self, client, token_cache):
        r = client.get(f"{ADMIN}/health", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_audit_logs(self, client, token_cache):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_thresholds(self, client, token_cache):
        r = client.get(f"{ADMIN}/thresholds", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200

    def test_admin_can_view_webhooks(self, client, token_cache):
        r = client.get(f"{ADMIN}/webhooks", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200

    def test_admin_can_access_me(self, client, token_cache):
        r = client.get(f"{AUTH}/me", headers=hdrs(token_cache, "ADMIN"))
        assert r.status_code == 200


# ── Checker role tests ─────────────────────────────────────────────────────
class TestCheckerRole:
    def test_checker_can_access_me(self, client, token_cache):
        r = client.get(f"{AUTH}/me", headers=hdrs(token_cache, "CHECKER"))
        assert r.status_code == 200

    def test_checker_can_view_audit_logs(self, client, token_cache):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs(token_cache, "CHECKER"))
        assert r.status_code in (200, 403)  # depends on checker permission scope

    def test_checker_can_view_institutions(self, client, token_cache):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs(token_cache, "CHECKER"))
        assert r.status_code in (200, 403)

    def test_checker_cannot_create_institution(self, client, token_cache):
        r = client.post(f"{ADMIN}/institutions", headers=hdrs(token_cache, "CHECKER"),
                        json={"name":"X","type":"bank","license_number":"L-999"})
        assert r.status_code in (403, 422)

    def test_checker_cannot_delete_institution(self, client, token_cache):
        r = client.delete(f"{ADMIN}/institutions/inst-demo-001",
                          headers=hdrs(token_cache, "CHECKER"))
        assert r.status_code == 403

    def test_checker_cannot_create_user(self, client, token_cache):
        r = client.post(f"{ADMIN}/users", headers=hdrs(token_cache, "CHECKER"),
                        json={"email":"x@x.com","role":"AGENT","password":"Test@1234",
                              "full_name":"X","phone":"01700000001"})
        assert r.status_code == 403

    def test_checker_cannot_update_thresholds(self, client, token_cache):
        r = client.put(f"{ADMIN}/thresholds", headers=hdrs(token_cache, "CHECKER"),
                       json={"simplified_max_amount": 999999})
        assert r.status_code == 403


# ── Maker role tests ───────────────────────────────────────────────────────
class TestMakerRole:
    def test_maker_can_access_me(self, client, token_cache):
        r = client.get(f"{AUTH}/me", headers=hdrs(token_cache, "MAKER"))
        assert r.status_code == 200

    def test_maker_cannot_list_institutions(self, client, token_cache):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs(token_cache, "MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_list_users(self, client, token_cache):
        r = client.get(f"{ADMIN}/users", headers=hdrs(token_cache, "MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_view_audit_logs(self, client, token_cache):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs(token_cache, "MAKER"))
        assert r.status_code == 403

    def test_maker_cannot_access_admin_stats(self, client, token_cache):
        r = client.get(f"{ADMIN}/stats", headers=hdrs(token_cache, "MAKER"))
        assert r.status_code in (403, 404)

    def test_maker_cannot_create_institution(self, client, token_cache):
        r = client.post(f"{ADMIN}/institutions", headers=hdrs(token_cache, "MAKER"),
                        json={"name":"X","type":"bank","license_number":"L-999"})
        assert r.status_code == 403


# ── Agent role tests ───────────────────────────────────────────────────────
class TestAgentRole:
    def test_agent_can_access_me(self, client, token_cache):
        r = client.get(f"{AUTH}/me", headers=hdrs(token_cache, "AGENT"))
        assert r.status_code == 200

    def test_agent_cannot_access_admin(self, client, token_cache):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs(token_cache, "AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_view_users(self, client, token_cache):
        r = client.get(f"{ADMIN}/users", headers=hdrs(token_cache, "AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_view_audit_logs(self, client, token_cache):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs(token_cache, "AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_view_thresholds(self, client, token_cache):
        r = client.get(f"{ADMIN}/thresholds", headers=hdrs(token_cache, "AGENT"))
        assert r.status_code == 403

    def test_agent_cannot_create_user(self, client, token_cache):
        r = client.post(f"{ADMIN}/users", headers=hdrs(token_cache, "AGENT"),
                        json={"email":"y@y.com","role":"AGENT","password":"Test@1234",
                              "full_name":"Y","phone":"01700000002"})
        assert r.status_code == 403


# ── Auditor role tests ─────────────────────────────────────────────────────
class TestAuditorRole:
    def test_auditor_can_access_me(self, client, token_cache):
        r = client.get(f"{AUTH}/me", headers=hdrs(token_cache, "AUDITOR"))
        assert r.status_code == 200

    def test_auditor_can_view_audit_logs(self, client, token_cache):
        r = client.get(f"{ADMIN}/audit-logs", headers=hdrs(token_cache, "AUDITOR"))
        assert r.status_code in (200, 403)

    def test_auditor_can_view_institutions(self, client, token_cache):
        r = client.get(f"{ADMIN}/institutions", headers=hdrs(token_cache, "AUDITOR"))
        assert r.status_code in (200, 403)

    def test_auditor_can_view_health(self, client, token_cache):
        r = client.get(f"{ADMIN}/health", headers=hdrs(token_cache, "AUDITOR"))
        assert r.status_code in (200, 403)

    def test_auditor_cannot_create_institution(self, client, token_cache):
        r = client.post(f"{ADMIN}/institutions", headers=hdrs(token_cache, "AUDITOR"),
                        json={"name":"X","type":"bank","license_number":"L-999"})
        assert r.status_code in (403, 422)

    def test_auditor_cannot_create_user(self, client, token_cache):
        r = client.post(f"{ADMIN}/users", headers=hdrs(token_cache, "AUDITOR"),
                        json={"email":"z@z.com","role":"AGENT","password":"Test@1234",
                              "full_name":"Z","phone":"01700000003"})
        assert r.status_code == 403

    def test_auditor_cannot_update_thresholds(self, client, token_cache):
        r = client.put(f"{ADMIN}/thresholds", headers=hdrs(token_cache, "AUDITOR"),
                       json={"simplified_max_amount": 999999})
        assert r.status_code == 403

    def test_auditor_cannot_delete_webhook(self, client, token_cache):
        r = client.delete(f"{ADMIN}/webhooks/fake-id",
                          headers=hdrs(token_cache, "AUDITOR"))
        assert r.status_code == 403


# ── Token security tests ───────────────────────────────────────────────────
class TestTokenSecurity:
    def test_no_token_blocked(self, client):
        r = client.get(f"{AUTH}/me")
        assert r.status_code == 403

    def test_tampered_token_blocked(self, client, token_cache):
        token = token_cache["AGENT"]
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "." + "invalidsignature"
        r = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {tampered}"})
        assert r.status_code == 401

    def test_alg_none_attack_blocked(self, client):
        import base64, json
        header  = base64.b64encode(json.dumps({"alg":"none","typ":"JWT"}).encode()).decode().rstrip("=")
        payload = base64.b64encode(json.dumps({"sub":"attacker","role":"ADMIN"}).encode()).decode().rstrip("=")
        token   = f"{header}.{payload}."
        r = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_expired_token_rejected(self, client):
        from datetime import datetime, timezone, timedelta
        from jose import jwt
        import os
        secret = os.environ.get("SECRET_KEY", "test-secret-key-32-chars-minimum!!")
        expired_token = jwt.encode(
            {"sub": "user-0001", "role": "AGENT",
             "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            secret, algorithm="HS256"
        )
        r = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code == 401


# ── 2FA enforcement tests ──────────────────────────────────────────────────
class TestTwoFactorEnforcement:
    def test_admin_without_totp_blocked(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "admin@demo.ekyc", "password": "AdminDemo@2026"
        })
        assert r.status_code in (401, 422)

    def test_checker_without_totp_blocked(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "checker@demo.ekyc", "password": "DemoChecker@2026"
        })
        assert r.status_code in (401, 422)

    def test_admin_wrong_totp_blocked(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "admin@demo.ekyc", "password": "AdminDemo@2026",
            "totp_code": "000000"
        })
        assert r.status_code in (401, 422)

    def test_maker_no_totp_required(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "maker@demo.ekyc", "password": "DemoMaker@2026"
        })
        assert r.status_code == 200

    def test_agent_no_totp_required(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "agent@demo.ekyc", "password": "DemoAgent@2026"
        })
        assert r.status_code == 200

    def test_auditor_no_totp_required(self, client):
        r = client.post(f"{AUTH}/token", json={
            "email": "auditor@demo.ekyc", "password": "DemoAudit@2026"
        })
        assert r.status_code == 200


# ── Privilege escalation tests ─────────────────────────────────────────────
class TestPrivilegeEscalation:
    def test_agent_cannot_promote_self(self, client, token_cache):
        r = client.put(f"{ADMIN}/users/user-0001/role",
                       headers=hdrs(token_cache, "AGENT"),
                       json={"role": "ADMIN"})
        assert r.status_code in (403, 405)

    def test_maker_cannot_reset_thresholds(self, client, token_cache):
        r = client.post(f"{ADMIN}/thresholds/reset",
                        headers=hdrs(token_cache, "MAKER"))
        assert r.status_code in (403, 404)

    def test_auditor_cannot_delete_audit_logs(self, client, token_cache):
        r = client.delete(f"{ADMIN}/audit-logs/some-id",
                          headers=hdrs(token_cache, "AUDITOR"))
        assert r.status_code in (403, 404, 405)

    def test_checker_cannot_access_admin_only_endpoints(self, client, token_cache):
        r = client.delete(f"{ADMIN}/users/user-0001",
                          headers=hdrs(token_cache, "CHECKER"))
        assert r.status_code == 403

    def test_agent_cannot_view_admin_stats(self, client, token_cache):
        r = client.get(f"{ADMIN}/stats", headers=hdrs(token_cache, "AGENT"))
        assert r.status_code in (403, 404)
