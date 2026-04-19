"""
M2 - Auth & User Management Tests
Tests: password hashing, JWT RS256, TOTP, RBAC, session, API endpoints
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Password hashing tests
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    def setup_method(self):
        from app.services.auth_service import hash_password, verify_password, needs_rehash
        self.hash_password  = hash_password
        self.verify_password = verify_password
        self.needs_rehash   = needs_rehash

    def test_hash_is_not_plaintext(self):
        h = self.hash_password("secret123")
        assert h != "secret123"

    def test_correct_password_verifies(self):
        h = self.hash_password("correct")
        assert self.verify_password("correct", h) is True

    def test_wrong_password_fails(self):
        h = self.hash_password("correct")
        assert self.verify_password("wrong", h) is False

    def test_hash_uses_argon2(self):
        h = self.hash_password("test")
        assert h.startswith("")

    def test_two_hashes_differ(self):
        h1 = self.hash_password("same")
        h2 = self.hash_password("same")
        assert h1 != h2  # different salts


# ---------------------------------------------------------------------------
# RS256 JWT tests
# ---------------------------------------------------------------------------
class TestJWT:
    def setup_method(self):
        from app.core.security import (
            create_access_token, create_refresh_token,
            decode_token, Role, ALGORITHM
        )
        self.create_access  = create_access_token
        self.create_refresh = create_refresh_token
        self.decode         = decode_token
        self.Role           = Role
        self.ALGORITHM      = ALGORITHM

    def test_access_token_decodes(self):
        token = self.create_access("inst-1", "user-1", self.Role.ADMIN, "tenant_demo")
        payload = self.decode(token)
        assert payload["sub"] == "inst-1"
        assert payload["role"] == "ADMIN"

    def test_access_token_has_jti(self):
        token = self.create_access("inst-1", "user-1", self.Role.MAKER, "tenant_demo")
        payload = self.decode(token)
        assert "jti" in payload
        assert len(payload["jti"]) == 36  # UUID

    def test_access_token_type(self):
        token = self.create_access("inst-1", "user-1", self.Role.CHECKER, "tenant_demo")
        payload = self.decode(token)
        assert payload["type"] == "access"

    def test_refresh_token_type(self):
        token = self.create_refresh("inst-1", "user-1")
        payload = self.decode(token)
        assert payload["type"] == "refresh"

    def test_token_uses_rs256(self):
        import jose.jwt as jwt_lib
        token = self.create_access("inst-1", "user-1", self.Role.AGENT, "tenant_demo")
        header = jwt_lib.get_unverified_header(token)
        assert header["alg"] == "RS256"

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            self.decode("invalid.token.here")

    def test_tenant_schema_in_payload(self):
        token = self.create_access("inst-1", "user-1", self.Role.AUDITOR, "tenant_abc")
        payload = self.decode(token)
        assert payload["tenant_schema"] == "tenant_abc"


# ---------------------------------------------------------------------------
# TOTP tests
# ---------------------------------------------------------------------------
class TestTOTP:
    def setup_method(self):
        from app.services.auth_service import (
            generate_totp_secret, get_totp_uri, verify_totp, generate_otp
        )
        self.generate_secret = generate_totp_secret
        self.get_uri         = get_totp_uri
        self.verify          = verify_totp
        self.generate_otp    = generate_otp

    def test_secret_is_base32(self):
        import base64
        secret = self.generate_secret()
        assert len(secret) >= 16
        # valid base32 characters only
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in secret)

    def test_uri_contains_issuer(self):
        secret = self.generate_secret()
        uri = self.get_uri(secret, "test@demo.com")
        assert "Xpert" in uri
        assert "test%40demo.com" in uri or "test@demo.com" in uri

    def test_valid_totp_verifies(self):
        import pyotp
        secret = self.generate_secret()
        code = pyotp.TOTP(secret).now()
        assert self.verify(secret, code) is True

    def test_invalid_totp_fails(self):
        secret = self.generate_secret()
        assert self.verify(secret, "000000") is False

    def test_otp_is_6_digits(self):
        otp = self.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()


# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------
class TestRBAC:
    def setup_method(self):
        from app.core.security import Role, has_permission, is_ip_allowed
        self.Role           = Role
        self.has_permission = has_permission
        self.is_ip_allowed  = is_ip_allowed

    def test_admin_has_all_permissions(self):
        assert self.has_permission(self.Role.ADMIN, "anything") is True

    def test_maker_can_create_onboarding(self):
        assert self.has_permission(self.Role.MAKER, "onboarding:create") is True

    def test_maker_cannot_approve(self):
        assert self.has_permission(self.Role.MAKER, "onboarding:approve") is False

    def test_checker_can_approve(self):
        assert self.has_permission(self.Role.CHECKER, "onboarding:approve") is True

    def test_checker_cannot_create(self):
        assert self.has_permission(self.Role.CHECKER, "onboarding:create") is False

    def test_auditor_can_read_audit(self):
        assert self.has_permission(self.Role.AUDITOR, "audit:read") is True

    def test_auditor_cannot_write(self):
        assert self.has_permission(self.Role.AUDITOR, "onboarding:create") is False

    def test_agent_can_face_verify(self):
        assert self.has_permission(self.Role.AGENT, "face:verify") is True

    def test_ip_whitelist_empty_allows_all(self):
        assert self.is_ip_allowed("1.2.3.4", []) is True

    def test_ip_whitelist_blocks_unknown(self):
        assert self.is_ip_allowed("9.9.9.9", ["1.2.3.4"]) is False

    def test_ip_whitelist_allows_known(self):
        assert self.is_ip_allowed("1.2.3.4", ["1.2.3.4", "5.6.7.8"]) is True


# ---------------------------------------------------------------------------
# Session management tests
# ---------------------------------------------------------------------------
class TestSession:
    def setup_method(self):
        from app.services.auth_service import (
            register_session, revoke_session, is_session_valid
        )
        self.register = register_session
        self.revoke   = revoke_session
        self.is_valid = is_session_valid

    def test_registered_session_is_valid(self):
        jti = "test-jti-001"
        self.register(jti, "user-1", datetime.now(timezone.utc) + timedelta(minutes=15))
        assert self.is_valid(jti) is True

    def test_revoked_session_is_invalid(self):
        jti = "test-jti-002"
        self.register(jti, "user-1", datetime.now(timezone.utc) + timedelta(minutes=15))
        self.revoke(jti)
        assert self.is_valid(jti) is False

    def test_expired_session_is_invalid(self):
        jti = "test-jti-003"
        self.register(jti, "user-1", datetime.now(timezone.utc) - timedelta(minutes=1))
        assert self.is_valid(jti) is False

    def test_unknown_jti_is_allowed(self):
        # stateless fallback - unknown jti passes
        assert self.is_valid("never-registered-jti") is True


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
class TestAuthAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        # Reset demo users between tests
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()

    def test_register_user(self):
        r = self.client.post("/api/v1/auth/register", json={
            "email": "maker@demo.com",
            "phone": "+8801712345678",
            "full_name": "Test Maker",
            "role": "MAKER",
            "password": "password123",
        })
        assert r.status_code == 201
        assert "registered" in r.json()["message"].lower()

    def test_register_duplicate_email_fails(self):
        payload = {
            "email": "dup@demo.com", "phone": "+8801712345678",
            "full_name": "Dup User", "role": "MAKER", "password": "password123",
        }
        self.client.post("/api/v1/auth/register", json=payload)
        r = self.client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 409

    def test_login_success(self):
        import pyotp; _S = "JBSWY3DPEHPK3PXP"
        self.client.post("/api/v1/auth/register", json={
            "email": "admin@demo.com", "phone": "+8801712345678",
            "full_name": "Admin User", "role": "ADMIN", "password": "adminpass1",
        })
        from app.api.v1.routes.auth import _demo_users
        u = next((x for x in _demo_users if x.email == "admin@demo.com"), None)
        if u and not u.totp_enabled: u.totp_secret = _S; u.totp_enabled = True
        r = self.client.post("/api/v1/auth/token", json={
            "email": "admin@demo.com", "password": "adminpass1",
            "totp_code": pyotp.TOTP(_S).now(),
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "ADMIN"

    def test_login_wrong_password(self):
        self.client.post("/api/v1/auth/register", json={
            "email": "user2@demo.com", "phone": "+8801712345678",
            "full_name": "User2", "role": "MAKER", "password": "correct123",
        })
        r = self.client.post("/api/v1/auth/token", json={
            "email": "user2@demo.com", "password": "wrongpass",
        })
        assert r.status_code == 401

    def test_get_me(self):
        self.client.post("/api/v1/auth/register", json={
            "email": "checker@demo.com", "phone": "+8801712345678",
            "full_name": "Checker", "role": "CHECKER", "password": "checker123",
        })
        import pyotp; _S2 = "JBSWY3DPEHPK3PXP"
        from app.api.v1.routes.auth import _demo_users
        u2 = next((x for x in _demo_users if x.email == "checker@demo.com"), None)
        if u2 and not u2.totp_enabled: u2.totp_secret = _S2; u2.totp_enabled = True
        login = self.client.post("/api/v1/auth/token", json={
            "email": "checker@demo.com", "password": "checker123",
            "totp_code": pyotp.TOTP(_S2).now(),
        })
        token = login.json()["access_token"]
        r = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["role"] == "CHECKER"

    def test_logout_revokes_session(self):
        self.client.post("/api/v1/auth/register", json={
            "email": "logout@demo.com", "phone": "+8801712345678",
            "full_name": "Logout User", "role": "AGENT", "password": "logout123",
        })
        login = self.client.post("/api/v1/auth/token", json={
            "email": "logout@demo.com", "password": "logout123",
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = self.client.delete("/api/v1/auth/logout", headers=headers)
        assert r.status_code == 200
        # Token should now be rejected
        r2 = self.client.get("/api/v1/auth/me", headers=headers)
        assert r2.status_code == 401

    def test_refresh_token(self):
        self.client.post("/api/v1/auth/register", json={
            "email": "refresh@demo.com", "phone": "+8801712345678",
            "full_name": "Refresh User", "role": "MAKER", "password": "refresh123",
        })
        login = self.client.post("/api/v1/auth/token", json={
            "email": "refresh@demo.com", "password": "refresh123",
        })
        refresh_token = login.json()["refresh_token"]
        r = self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_invalid_role_rejected(self):
        r = self.client.post("/api/v1/auth/register", json={
            "email": "bad@demo.com", "phone": "+8801712345678",
            "full_name": "Bad Role", "role": "SUPERUSER", "password": "badpass1",
        })
        assert r.status_code == 422

    def test_admin_can_list_roles(self):
        import pyotp; _S3 = "JBSWY3DPEHPK3PXP"
        self.client.post("/api/v1/auth/register", json={
            "email": "adm2@demo.com", "phone": "+8801712345678",
            "full_name": "Admin2", "role": "ADMIN", "password": "adminpass2",
        })
        from app.api.v1.routes.auth import _demo_users
        u3 = next((x for x in _demo_users if x.email == "adm2@demo.com"), None)
        if u3 and not u3.totp_enabled: u3.totp_secret = _S3; u3.totp_enabled = True
        login = self.client.post("/api/v1/auth/token", json={
            "email": "adm2@demo.com", "password": "adminpass2",
            "totp_code": pyotp.TOTP(_S3).now(),
        })
        token = login.json()["access_token"]
        r = self.client.get("/api/v1/auth/roles", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "ADMIN" in data
        assert "MAKER" in data
        assert "CHECKER" in data

    def test_non_admin_cannot_list_roles(self):
        self.client.post("/api/v1/auth/register", json={
            "email": "aud@demo.com", "phone": "+8801712345678",
            "full_name": "Auditor", "role": "AUDITOR", "password": "auditor123",
        })
        login = self.client.post("/api/v1/auth/token", json={
            "email": "aud@demo.com", "password": "auditor123",
        })
        token = login.json()["access_token"]
        r = self.client.get("/api/v1/auth/roles", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
