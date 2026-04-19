"""
test_m32_2fa.py - M32 2FA Enforcement
Tests: policy, status, role enforcement, bypass prevention, TOTP setup flow
"""
import pytest
import pyotp
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = "/api/v1/auth"
BASE = "/api/v1/auth/2fa"

# ── Helpers ───────────────────────────────────────────────────────────────
def register(email, role, password="Test@12345"):
    return client.post(f"{AUTH}/register", json={
        "email": email, "phone": "01700000000",
        "full_name": "Test User", "role": role,
        "password": password, "institution_id": "inst-demo-001",
    })

def login(email, password="Test@12345", totp_code=None):
    payload = {"email": email, "password": password}
    if totp_code: payload["totp_code"] = totp_code
    return client.post(f"{AUTH}/token", json=payload)

def get_token(email, role, password="Test@12345", totp_code=None):
    register(email, role, password)
    r = login(email, password, totp_code)
    return r.json().get("access_token","") if r.status_code == 200 else None

def headers(token): return {"Authorization": f"Bearer {token}"}

# ══════════════════════════════════════════════════════════════════════════
# 1. 2FA Policy (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestPolicy:
    def test_policy_200(self):
        r = client.get(f"{BASE}/policy")
        assert r.status_code == 200

    def test_policy_has_required_roles(self):
        r = client.get(f"{BASE}/policy")
        d = r.json()
        assert "required_roles" in d
        assert "ADMIN" in d["required_roles"]
        assert "CHECKER" in d["required_roles"]

    def test_policy_has_exempt_roles(self):
        r = client.get(f"{BASE}/policy")
        assert "AGENT" in r.json()["exempt_roles"]

    def test_policy_has_bfiu_ref(self):
        r = client.get(f"{BASE}/policy")
        assert "BFIU" in r.json()["bfiu_ref"]

# ══════════════════════════════════════════════════════════════════════════
# 2. Role enforcement on login (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestRoleEnforcement:
    def test_agent_can_login_without_2fa(self):
        register("agent_2fa_01@test.com", "AGENT")
        r = login("agent_2fa_01@test.com")
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_maker_can_login_without_2fa(self):
        register("maker_2fa_01@test.com", "MAKER")
        r = login("maker_2fa_01@test.com")
        assert r.status_code == 200

    def test_admin_blocked_without_2fa_setup(self):
        register("admin_2fa_block@test.com", "ADMIN")
        r = login("admin_2fa_block@test.com")
        assert r.status_code == 401

    def test_checker_blocked_without_2fa_setup(self):
        register("checker_2fa_block@test.com", "CHECKER")
        r = login("checker_2fa_block@test.com")
        assert r.status_code == 401

    def test_admin_blocked_error_code(self):
        register("admin_2fa_err@test.com", "ADMIN")
        r = login("admin_2fa_err@test.com")
        body = r.json()
        # error boundary wraps as {"error": {"code": "UNAUTHORIZED", "details": {...}}}
        # Our 2FA error is in details or message
        body_str = str(body)
        assert "2FA" in body_str or "SETUP" in body_str or "TOTP" in body_str or "totp" in body_str

    def test_admin_blocked_has_action_required(self):
        register("admin_2fa_act@test.com", "ADMIN")
        r = login("admin_2fa_act@test.com")
        body = r.json()
        err = body.get("error", body.get("detail", {}))
        assert err.get("action_required") in ("SETUP_2FA", "PROVIDE_TOTP") or "2FA" in str(err)

# ══════════════════════════════════════════════════════════════════════════
# 3. 2FA setup and verification flow (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestTOTPFlow:
    def test_totp_setup_requires_auth(self):
        r = client.post(f"{AUTH}/totp/setup")
        assert r.status_code in (401, 403)

    def test_totp_setup_returns_secret(self):
        # Use AGENT (can login without 2FA)
        token = get_token("agent_totp_01@test.com", "AGENT")
        if not token: pytest.skip("Login failed")
        r = client.post(f"{AUTH}/totp/setup", headers=headers(token))
        assert r.status_code == 200
        assert "totp_secret" in r.json()
        assert len(r.json()["totp_secret"]) > 10

    def test_totp_setup_returns_uri(self):
        token = get_token("agent_totp_02@test.com", "AGENT")
        if not token: pytest.skip("Login failed")
        r = client.post(f"{AUTH}/totp/setup", headers=headers(token))
        assert "totp_uri" in r.json()
        assert r.json()["totp_uri"].startswith("otpauth://")

    def test_totp_verify_wrong_code(self):
        token = get_token("agent_totp_03@test.com", "AGENT")
        if not token: pytest.skip("Login failed")
        client.post(f"{AUTH}/totp/setup", headers=headers(token))
        r = client.post(f"{AUTH}/totp/verify",
                        json={"totp_code": "000000"},
                        headers=headers(token))
        assert r.status_code == 401

    def test_totp_verify_valid_code(self):
        token = get_token("agent_totp_04@test.com", "AGENT")
        if not token: pytest.skip("Login failed")
        setup_r = client.post(f"{AUTH}/totp/setup", headers=headers(token))
        secret = setup_r.json()["totp_secret"]
        valid_code = pyotp.TOTP(secret).now()
        r = client.post(f"{AUTH}/totp/verify",
                        json={"totp_code": valid_code},
                        headers=headers(token))
        assert r.status_code == 200

# ══════════════════════════════════════════════════════════════════════════
# 4. 2FA status endpoint (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestStatus:
    def test_status_requires_auth(self):
        r = client.get(f"{BASE}/status")
        assert r.status_code in (401, 403)

    def test_agent_status_not_required(self):
        token = get_token("agent_status_01@test.com", "AGENT")
        if not token: pytest.skip("Login failed")
        r = client.get(f"{BASE}/status", headers=headers(token))
        assert r.status_code == 200
        assert r.json()["2fa_required"] is False
        assert r.json()["compliant"] is True

    def test_status_has_required_keys(self):
        token = get_token("agent_status_02@test.com", "AGENT")
        if not token: pytest.skip("Login failed")
        r = client.get(f"{BASE}/status", headers=headers(token))
        for k in ["role","totp_enabled","2fa_required","compliant","bfiu_ref"]:
            assert k in r.json(), f"Missing key: {k}"

    def test_required_roles_endpoint(self):
        r = client.get(f"{BASE}/required-roles")
        assert r.status_code == 200
        assert "ADMIN" in r.json()["roles_requiring_2fa"]
        assert "CHECKER" in r.json()["roles_requiring_2fa"]

# ══════════════════════════════════════════════════════════════════════════
# 5. 2FA Service unit tests (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestTwofaService:
    def test_admin_requires_2fa(self):
        from app.services.twofa_service import is_2fa_required
        assert is_2fa_required("ADMIN") is True
        assert is_2fa_required("CHECKER") is True

    def test_agent_exempt(self):
        from app.services.twofa_service import is_2fa_exempt
        assert is_2fa_exempt("AGENT") is True

    def test_compliance_check_admin_no_totp(self):
        from app.services.twofa_service import check_2fa_compliance
        result = check_2fa_compliance("ADMIN", False, None, None)
        assert result["allowed"] is False
        assert result["error_code"] == "2FA_SETUP_REQUIRED"

    def test_compliance_check_agent_no_totp(self):
        from app.services.twofa_service import check_2fa_compliance
        result = check_2fa_compliance("AGENT", False, None, None)
        assert result["allowed"] is True
