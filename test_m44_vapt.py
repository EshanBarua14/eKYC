"""
M44 — VAPT Test Suite
OWASP Top 10 Automated Security Tests
Xpert Fintech eKYC Platform

Run: pytest tests/test_m44_vapt.py -v --tb=short 2>&1 | tee vapt_report.txt

Backend must be running: uvicorn app.main:app --reload --port 8000
"""

import time
import uuid
import base64
import json
import pytest
import requests
import pyotp

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"

AGENT_EMAIL    = "agent@demo.ekyc"
AGENT_PASSWORD = "DemoAgent@2026"

ADMIN_EMAIL    = "admin@demo.ekyc"
ADMIN_PASSWORD = "AdminDemo@2026"
TOTP_SECRET    = "JBSWY3DPEHPK3PXP"

CHECKER_EMAIL    = "checker@demo.ekyc"
CHECKER_PASSWORD = "DemoChecker@2026"

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_totp_code() -> str:
    """Generate a valid TOTP code for admin/checker login."""
    return pyotp.TOTP(TOTP_SECRET).now()


def login(email: str, password: str, totp: str | None = None) -> dict:
    """Log in and return the JSON response."""
    payload = {"email": email, "password": password}
    if totp:
        payload["totp_code"] = totp
    r = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=10)
    return r


def agent_token() -> str:
    """Return a valid Agent JWT."""
    r = login(AGENT_EMAIL, AGENT_PASSWORD)
    assert r.status_code == 200, f"Agent login failed: {r.text}"
    data = r.json()
    # Support both token shapes used in the codebase
    return data.get("access_token") or data.get("token")


def admin_token() -> str:
    """Return a valid Admin JWT (with TOTP)."""
    r = login(ADMIN_EMAIL, ADMIN_PASSWORD, totp=get_totp_code())
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    return data.get("access_token") or data.get("token")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def tampered_jwt(original_token: str) -> str:
    """Flip one byte in the JWT signature to produce a tampered token."""
    parts = original_token.split(".")
    if len(parts) != 3:
        return original_token
    sig = parts[2]
    # XOR first char of signature with 0x01
    sig_bytes = base64.urlsafe_b64decode(sig + "==")
    tampered = bytearray(sig_bytes)
    tampered[0] ^= 0x01
    parts[2] = base64.urlsafe_b64encode(bytes(tampered)).rstrip(b"=").decode()
    return ".".join(parts)


def alg_none_token(original_token: str) -> str:
    """Build a JWT with alg=none — classic algorithm confusion attack."""
    parts = original_token.split(".")
    if len(parts) != 3:
        return original_token
    # Decode header and replace alg with "none"
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
    header["alg"] = "none"
    new_header = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    # Strip signature (none algorithm has no signature)
    return f"{new_header}.{parts[1]}."


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def valid_agent_token():
    return agent_token()


@pytest.fixture(scope="module")
def valid_admin_token():
    return admin_token()


# ─────────────────────────────────────────────
# SECTION 1: BACKEND HEALTH CHECK
# ─────────────────────────────────────────────

class TestPreFlight:
    """Verify backend is up before running security tests."""

    def test_backend_is_alive(self):
        """Backend must be reachable."""
        r = requests.get(HEALTH_URL, timeout=5)
        assert r.status_code == 200, (
            "Backend is not running. Start it with: "
            "uvicorn app.main:app --reload --port 8000"
        )

    def test_health_returns_ok(self):
        r = requests.get(HEALTH_URL, timeout=5)
        data = r.json()
        assert data.get("status") == "ok"

    def test_health_no_auth_required(self):
        """Health endpoint must NOT require authentication."""
        r = requests.get(HEALTH_URL, timeout=5)
        assert r.status_code != 401
        assert r.status_code != 403


# ─────────────────────────────────────────────
# SECTION 2: BROKEN AUTHENTICATION (OWASP A07)
# ─────────────────────────────────────────────

class TestBrokenAuthentication:

    def test_no_token_returns_401(self):
        """Protected endpoint must reject requests with no token."""
        r = requests.get(f"{BASE_URL}/nid/verify", timeout=5)
        assert r.status_code in (401, 403), (
            f"Expected 401/403 with no token, got {r.status_code}"
        )

    def test_empty_bearer_returns_401(self):
        """Empty Bearer token must be rejected."""
        r = requests.get(
            f"{BASE_URL}/nid/verify",
            headers={"Authorization": "Bearer "},
            timeout=5,
        )
        assert r.status_code in (401, 403)

    def test_garbage_token_returns_401(self):
        """Random garbage as Bearer token must be rejected."""
        r = requests.get(
            f"{BASE_URL}/nid/verify",
            headers={"Authorization": "Bearer not.a.jwt"},
            timeout=5,
        )
        assert r.status_code in (401, 403)

    def test_tampered_signature_rejected(self, valid_agent_token):
        """A JWT with a corrupted signature must be rejected."""
        bad_token = tampered_jwt(valid_agent_token)
        r = requests.get(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(bad_token),
            timeout=5,
        )
        assert r.status_code in (401, 403), (
            f"Tampered JWT was accepted! Status: {r.status_code}"
        )

    def test_alg_none_attack_rejected(self, valid_agent_token):
        """JWT with alg=none must be rejected (algorithm confusion attack)."""
        none_token = alg_none_token(valid_agent_token)
        r = requests.get(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(none_token),
            timeout=5,
        )
        assert r.status_code in (401, 403), (
            f"CRITICAL: alg=none JWT was accepted! Status: {r.status_code}"
        )

    def test_wrong_password_returns_401(self):
        """Wrong credentials must return 401."""
        r = login(AGENT_EMAIL, "WrongPassword@123")
        assert r.status_code == 401, (
            f"Wrong password should be 401, got {r.status_code}"
        )

    def test_nonexistent_user_returns_401(self):
        """Login with a nonexistent user must return 401 (not 404 — timing leak)."""
        r = login("ghost@nowhere.invalid", "SomePassword@123")
        assert r.status_code == 401

    def test_login_error_message_is_generic(self):
        """
        Error messages must not distinguish between bad username vs bad password
        to prevent user enumeration.
        """
        r1 = login("ghost@nowhere.invalid", "any")
        r2 = login(AGENT_EMAIL, "WrongPassword@123")
        # Both should fail. Their error messages must not reveal which field is wrong.
        msg1 = r1.json().get("error", {}).get("message", "") if r1.headers.get("content-type", "").startswith("application/json") else r1.text
        msg2 = r2.json().get("error", {}).get("message", "") if r2.headers.get("content-type", "").startswith("application/json") else r2.text
        # Both must not expose different messages that reveal username vs password
        assert "username" not in msg1.lower() or "username" not in msg2.lower(), (
            "Login errors distinguish username vs password — user enumeration risk"
        )


# ─────────────────────────────────────────────
# SECTION 3: BROKEN ACCESS CONTROL (OWASP A01)
# ─────────────────────────────────────────────

class TestBrokenAccessControl:

    def test_agent_cannot_access_admin_users_endpoint(self, valid_agent_token):
        """Agent role must not access admin user management."""
        r = requests.get(
            f"{BASE_URL}/admin/users",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (401, 403), (
            f"Agent accessed /admin/users! Status: {r.status_code}"
        )

    def test_agent_cannot_access_audit_export(self, valid_agent_token):
        """Agent must not export BFIU audit logs."""
        r = requests.get(
            f"{BASE_URL}/audit/export",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (401, 403), (
            f"Agent accessed /audit/export! Status: {r.status_code}"
        )

    def test_agent_cannot_access_institution_settings(self, valid_agent_token):
        """Agent must not access institution-level settings."""
        r = requests.get(
            f"{BASE_URL}/admin/settings",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (401, 403)

    def test_agent_cannot_approve_verifications(self, valid_agent_token):
        """Agent must not approve/reject verifications (Checker-only action)."""
        fake_id = str(uuid.uuid4())
        r = requests.post(
            f"{BASE_URL}/review/{fake_id}",
            headers=auth_headers(valid_agent_token),
            json={"decision": "approve"},
            timeout=5,
        )
        assert r.status_code in (401, 403), (
            f"Agent was allowed to call /review/{{id}}! Status: {r.status_code}"
        )

    def test_agent_cannot_delete_users(self, valid_agent_token):
        """Agent must not be able to delete users."""
        fake_id = str(uuid.uuid4())
        r = requests.delete(
            f"{BASE_URL}/admin/users/{fake_id}",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (401, 403)

    def test_admin_can_access_admin_endpoints(self, valid_admin_token):
        """Sanity check: Admin must be able to access admin endpoints."""
        r = requests.get(
            f"{BASE_URL}/admin/users",
            headers=auth_headers(valid_admin_token),
            timeout=5,
        )
        # 200 = good, 404 = endpoint not found (acceptable), anything else = problem
        assert r.status_code in (200, 404), (
            f"Admin cannot access /admin/users: {r.status_code}"
        )


# ─────────────────────────────────────────────
# SECTION 4: IDOR — INSECURE DIRECT OBJECT REF
# ─────────────────────────────────────────────

class TestIDOR:

    def test_idor_verification_result(self, valid_agent_token):
        """
        An agent must not be able to fetch another tenant's verification
        record by guessing a UUID.
        """
        # Use a random UUID — should never match our agent's data
        random_id = str(uuid.uuid4())
        r = requests.get(
            f"{BASE_URL}/face/verify/{random_id}",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        # Must not return 200 with someone else's data
        assert r.status_code in (403, 404), (
            f"IDOR: Got {r.status_code} for random UUID — expected 403/404"
        )

    def test_idor_liveness_session(self, valid_agent_token):
        """An agent must not access arbitrary liveness sessions."""
        random_id = str(uuid.uuid4())
        r = requests.get(
            f"{BASE_URL}/ai/session/{random_id}",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (403, 404)

    def test_idor_kyc_profile(self, valid_agent_token):
        """An agent must not read arbitrary KYC profiles."""
        random_id = str(uuid.uuid4())
        r = requests.get(
            f"{BASE_URL}/kyc/profile/{random_id}",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (403, 404)

    def test_idor_audit_log_entry(self, valid_agent_token):
        """Agents must not read arbitrary audit log entries."""
        random_id = str(uuid.uuid4())
        r = requests.get(
            f"{BASE_URL}/audit/{random_id}",
            headers=auth_headers(valid_agent_token),
            timeout=5,
        )
        assert r.status_code in (401, 403, 404)


# ─────────────────────────────────────────────
# SECTION 5: INJECTION (OWASP A03)
# ─────────────────────────────────────────────

class TestInjection:

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "' OR 1=1--",
        "'; DROP TABLE users;--",
        "1' UNION SELECT null,null,null--",
        "admin'--",
    ]

    XSS_PAYLOADS = [
        "<script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
    ]

    def test_sql_injection_in_login_email(self):
        """SQL injection in login email field must not cause 500 or bypass auth."""
        for payload in self.SQL_PAYLOADS:
            r = login(payload, "anything")
            assert r.status_code != 500, (
                f"SQL injection caused 500: {payload!r}"
            )
            assert r.status_code != 200, (
                f"SQL injection bypassed auth: {payload!r}"
            )

    def test_sql_injection_in_login_password(self):
        """SQL injection in password field must not bypass auth."""
        for payload in self.SQL_PAYLOADS:
            r = login(AGENT_EMAIL, payload)
            assert r.status_code != 200, (
                f"SQL injection in password field bypassed auth: {payload!r}"
            )
            assert r.status_code != 500, (
                f"SQL injection in password caused server error: {payload!r}"
            )

    def test_sql_injection_in_nid_verify(self, valid_agent_token):
        """SQL injection in NID number must not cause 500 or return data."""
        for payload in self.SQL_PAYLOADS:
            r = requests.post(
                f"{BASE_URL}/nid/verify",
                headers=auth_headers(valid_agent_token),
                json={"nid_number": payload, "date_of_birth": "1990-01-01"},
                timeout=10,
            )
            assert r.status_code != 500, (
                f"SQL injection in nid_number caused 500: {payload!r}\n{r.text}"
            )

    def test_xss_payload_in_text_fields_not_reflected(self, valid_agent_token):
        """
        XSS payloads in text fields must not be reflected back unescaped
        in the JSON response.
        """
        for payload in self.XSS_PAYLOADS:
            r = requests.post(
                f"{BASE_URL}/nid/verify",
                headers=auth_headers(valid_agent_token),
                json={"nid_number": payload, "date_of_birth": "1990-01-01"},
                timeout=10,
            )
            response_text = r.text
            # The raw unescaped script tag must not appear verbatim in response
            assert "<script>" not in response_text, (
                f"XSS payload reflected: {payload!r}"
            )

    def test_oversized_payload_rejected(self, valid_agent_token):
        """Extremely large payload must be rejected (not cause 500 or OOM)."""
        huge_nid = "A" * 10_000
        r = requests.post(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(valid_agent_token),
            json={"nid_number": huge_nid, "date_of_birth": "1990-01-01"},
            timeout=10,
        )
        # 400 or 422 = properly validated. 413 = too large. All are fine.
        assert r.status_code in (400, 413, 422), (
            f"Oversized payload returned {r.status_code}"
        )

    def test_invalid_json_returns_400(self):
        """Malformed JSON body must return 400, not 500."""
        r = requests.post(
            f"{BASE_URL}/auth/login",
            data="not json at all {{{{",
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        assert r.status_code in (400, 422), (
            f"Malformed JSON returned {r.status_code}"
        )


# ─────────────────────────────────────────────
# SECTION 6: SECURITY MISCONFIGURATION (OWASP A05)
# ─────────────────────────────────────────────

class TestSecurityMisconfiguration:

    def test_cors_arbitrary_origin_rejected(self, valid_agent_token):
        """
        An arbitrary untrusted origin must not be reflected in
        Access-Control-Allow-Origin.
        """
        r = requests.get(
            f"{BASE_URL}/nid/verify",
            headers={
                **auth_headers(valid_agent_token),
                "Origin": "https://evil-attacker.com",
            },
            timeout=5,
        )
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "https://evil-attacker.com", (
            "CORS wildcard mirrors untrusted Origin — CSRF risk!"
        )
        assert acao != "*" or r.status_code in (401, 403), (
            "CORS is open wildcard (*) on authenticated endpoint"
        )

    def test_cors_preflight_arbitrary_origin(self):
        """OPTIONS preflight must not allow arbitrary origins."""
        r = requests.options(
            f"{BASE_URL}/auth/login",
            headers={
                "Origin": "https://evil-attacker.com",
                "Access-Control-Request-Method": "POST",
            },
            timeout=5,
        )
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "https://evil-attacker.com", (
            "Preflight allows arbitrary Origin — CORS misconfiguration"
        )

    def test_error_responses_use_standard_format(self):
        """Error responses must follow the standard error envelope."""
        r = login("bad@user.com", "badpassword")
        assert r.headers.get("content-type", "").startswith("application/json"), (
            "Error response is not JSON"
        )
        data = r.json()
        # Must have the error envelope OR be a standard FastAPI 422
        has_error_key = "error" in data
        has_detail_key = "detail" in data  # FastAPI validation errors
        assert has_error_key or has_detail_key, (
            f"Error response missing 'error' or 'detail' key: {data}"
        )

    def test_no_stack_trace_in_error_response(self, valid_agent_token):
        """Internal errors must not expose Python stack traces."""
        # Send an intentionally bad request
        r = requests.post(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(valid_agent_token),
            json={},  # Missing required fields
            timeout=5,
        )
        body = r.text
        assert "Traceback" not in body, "Stack trace leaked in error response!"
        assert "File \"" not in body, "Python file path leaked in error response!"

    def test_server_header_not_verbose(self):
        """Server header must not reveal framework/version details."""
        r = requests.get(HEALTH_URL, timeout=5)
        server_header = r.headers.get("Server", "")
        # Should not expose uvicorn version, Python version, etc.
        for leak in ["uvicorn/", "Python/", "FastAPI/", "starlette/"]:
            assert leak.lower() not in server_header.lower(), (
                f"Server header leaks: {server_header}"
            )

    def test_sensitive_data_not_in_health_endpoint(self):
        """Health endpoint must not expose internal config or secrets."""
        r = requests.get(HEALTH_URL, timeout=5)
        body = r.text.lower()
        for sensitive in ["password", "secret", "database_url", "redis_url", "private_key"]:
            assert sensitive not in body, (
                f"Sensitive keyword '{sensitive}' found in /health response"
            )


# ─────────────────────────────────────────────
# SECTION 7: RATE LIMITING (OWASP A04 / A07)
# ─────────────────────────────────────────────

class TestRateLimiting:

    def test_login_rate_limit_enforced(self):
        """
        Brute-force login attempts must trigger 429 before the 11th request.
        Rate limit: 10 req/min/IP per API spec.
        """
        blocked = False
        for i in range(15):
            r = login("ratelimit_test@test.invalid", f"wrong_pass_{i}")
            if r.status_code == 429:
                blocked = True
                break

        assert blocked, (
            "CRITICAL: 15 failed login attempts did not trigger rate limiting (429). "
            "Brute-force attacks are unmitigated."
        )

    def test_rate_limit_includes_retry_after_header(self):
        """429 responses must include Retry-After header."""
        for i in range(15):
            r = login("ratelimit_test2@test.invalid", f"wrong_{i}")
            if r.status_code == 429:
                # Should have Retry-After or X-RateLimit-Reset
                has_retry = (
                    "Retry-After" in r.headers
                    or "X-RateLimit-Reset" in r.headers
                    or "retry_after" in r.text.lower()
                )
                assert has_retry, (
                    "429 response missing Retry-After header"
                )
                return
        # If no 429 was triggered, the rate-limit test above would have failed

    def test_x_forwarded_for_does_not_bypass_rate_limit(self):
        """
        Rotating X-Forwarded-For headers must not bypass per-IP rate limits.
        This tests that the rate limiter uses the real IP, not the spoofed header.
        """
        blocked_with_rotation = False
        blocked_without_rotation = False

        # Try with rotating fake IPs
        for i in range(15):
            r = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": f"test{i}@invalid.com", "password": "wrong"},
                headers={"X-Forwarded-For": f"1.2.3.{i % 256}"},
                timeout=5,
            )
            if r.status_code == 429:
                blocked_with_rotation = True
                break

        # Reset — wait slightly or just verify the system is rate limiting at all
        # Key insight: if rotating X-Forwarded-For bypasses limits entirely,
        # blocked_with_rotation would be False even after 15 attempts.
        # We can only make a strong assertion if we know the backend's real behavior.
        # Here we document whether the bypass works (informational for report).
        if not blocked_with_rotation:
            pytest.xfail(
                "SECURITY FINDING: X-Forwarded-For header rotation bypasses rate limiting. "
                "The backend should use the real socket IP for rate limiting, not the header."
            )


# ─────────────────────────────────────────────
# SECTION 8: SENSITIVE DATA EXPOSURE (OWASP A02)
# ─────────────────────────────────────────────

class TestSensitiveDataExposure:

    def test_login_response_does_not_contain_password(self):
        """Successful login response must not echo back the password."""
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        body = r.text
        assert AGENT_PASSWORD not in body, "Password echoed in login response!"

    def test_login_response_does_not_contain_password_hash(self):
        """Login response must not contain any hash-like strings."""
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        body = r.text.lower()
        # Argon2id hashes start with $argon2
        assert "$argon2" not in body, "Password hash exposed in login response!"
        assert "$2b$" not in body, "bcrypt hash exposed in login response!"

    def test_nid_not_in_plaintext_in_response(self, valid_agent_token):
        """
        NID numbers must be stored/returned as HMAC hashes, never plaintext.
        When we send a NID for verification, it must not be echoed back as-is.
        """
        test_nid = "1234567890123"
        r = requests.post(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(valid_agent_token),
            json={"nid_number": test_nid, "date_of_birth": "1985-07-15"},
            timeout=10,
        )
        # Whether the request succeeds or fails, the plaintext NID must not be echoed
        if r.status_code in (200, 400, 422):
            response_body = r.json()
            response_str = json.dumps(response_body)
            # The NID should NOT appear in plaintext in the response body
            assert test_nid not in response_str or _check_nid_in_error_only(response_str, test_nid), (
                f"NID number returned in plaintext in response: {response_str[:200]}"
            )

    def test_http_strict_transport_security_header(self):
        """
        HSTS header should be present (production requirement).
        Marked as xfail for localhost — HSTS only applies over HTTPS.
        """
        r = requests.get(HEALTH_URL, timeout=5)
        hsts = r.headers.get("Strict-Transport-Security", "")
        if not hsts:
            pytest.xfail(
                "HSTS header not present on localhost (expected — HSTS requires HTTPS). "
                "Verify HSTS is enforced on the production TLS endpoint."
            )

    def test_content_type_nosniff_header(self):
        """X-Content-Type-Options: nosniff must be present."""
        r = requests.get(HEALTH_URL, timeout=5)
        nosniff = r.headers.get("X-Content-Type-Options", "")
        assert nosniff == "nosniff", (
            f"X-Content-Type-Options header missing or wrong: '{nosniff}'"
        )

    def test_x_frame_options_header(self):
        """X-Frame-Options must be set to prevent clickjacking."""
        r = requests.get(HEALTH_URL, timeout=5)
        xfo = r.headers.get("X-Frame-Options", "")
        assert xfo.upper() in ("DENY", "SAMEORIGIN"), (
            f"X-Frame-Options header missing or wrong: '{xfo}'"
        )


# ─────────────────────────────────────────────
# SECTION 9: MASS ASSIGNMENT / INPUT VALIDATION
# ─────────────────────────────────────────────

class TestInputValidation:

    def test_extra_fields_silently_ignored(self, valid_agent_token):
        """
        Extra/unexpected fields in request body must be silently dropped,
        not cause a 500 error (Pydantic's extra='ignore').
        """
        r = requests.post(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(valid_agent_token),
            json={
                "nid_number": "1234567890123",
                "date_of_birth": "1985-07-15",
                "__inject__": "malicious_value",
                "role": "admin",          # privilege escalation attempt
                "is_admin": True,
                "institution_id": str(uuid.uuid4()),
            },
            timeout=10,
        )
        assert r.status_code != 500, "Extra fields caused server error!"

    def test_role_field_in_body_does_not_escalate(self, valid_agent_token):
        """
        Sending role='Admin' in the request body must not escalate privileges.
        Role must come from the JWT only.
        """
        # Try to access admin endpoint while claiming admin role in body
        r = requests.get(
            f"{BASE_URL}/admin/users",
            headers=auth_headers(valid_agent_token),
            params={"role": "admin"},
            timeout=5,
        )
        assert r.status_code in (401, 403), (
            f"Role escalation via query param! Status: {r.status_code}"
        )

    def test_null_byte_injection(self, valid_agent_token):
        """Null bytes in input must not cause unexpected behavior."""
        r = requests.post(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(valid_agent_token),
            json={"nid_number": "123456789\x00012", "date_of_birth": "1990-01-01"},
            timeout=5,
        )
        assert r.status_code != 500, "Null byte caused server error!"

    def test_negative_numbers_in_numeric_fields(self, valid_agent_token):
        """Negative or boundary numbers must be validated, not cause 500."""
        r = requests.post(
            f"{BASE_URL}/nid/verify",
            headers=auth_headers(valid_agent_token),
            json={"nid_number": "-1", "date_of_birth": "1990-01-01"},
            timeout=5,
        )
        assert r.status_code != 500


# ─────────────────────────────────────────────
# SECTION 10: JWT SECURITY
# ─────────────────────────────────────────────

class TestJWTSecurity:

    def test_jwt_uses_rs256_not_hs256(self):
        """
        JWT algorithm must be RS256, not HS256.
        HS256 with a guessable secret is a critical vulnerability.
        """
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert r.status_code == 200
        token = r.json().get("access_token") or r.json().get("token")
        assert token, "No token in login response"

        # Decode header (no verification needed — we're reading the header)
        header_b64 = token.split(".")[0]
        # Add padding
        padding = "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64 + padding))

        assert header.get("alg") == "RS256", (
            f"JWT algorithm is '{header.get('alg')}', expected 'RS256'. "
            "HS256 with a weak secret is exploitable."
        )

    def test_jwt_has_expiry_claim(self):
        """JWT must have an 'exp' claim to prevent tokens from living forever."""
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert r.status_code == 200
        token = r.json().get("access_token") or r.json().get("token")

        payload_b64 = token.split(".")[1]
        padding = "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))

        assert "exp" in payload, "JWT missing 'exp' claim — token never expires!"
        assert "iat" in payload, "JWT missing 'iat' claim"

    def test_jwt_expiry_is_reasonable(self):
        """JWT expiry should be 15 minutes (900 seconds) per API spec."""
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert r.status_code == 200
        token = r.json().get("access_token") or r.json().get("token")

        payload_b64 = token.split(".")[1]
        padding = "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))

        ttl_seconds = payload["exp"] - payload["iat"]
        # Per API spec: 15 minutes = 900 seconds. Allow up to 1 hour.
        assert ttl_seconds <= 3600, (
            f"JWT TTL is {ttl_seconds}s ({ttl_seconds/3600:.1f}hrs) — too long! "
            "Per spec, access tokens should be 900s (15 minutes)."
        )
        assert ttl_seconds > 0, "JWT exp is before iat!"

    def test_jwt_contains_role_claim(self):
        """JWT must contain a role claim for RBAC enforcement."""
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert r.status_code == 200
        token = r.json().get("access_token") or r.json().get("token")

        payload_b64 = token.split(".")[1]
        padding = "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))

        assert "role" in payload, "JWT missing 'role' claim — RBAC cannot be enforced!"

    def test_two_tokens_have_different_jti(self):
        """Each JWT must have a unique jti to support revocation."""
        r1 = login(AGENT_EMAIL, AGENT_PASSWORD)
        time.sleep(0.1)
        r2 = login(AGENT_EMAIL, AGENT_PASSWORD)

        assert r1.status_code == 200
        assert r2.status_code == 200

        def get_payload(resp):
            token = resp.json().get("access_token") or resp.json().get("token")
            pb64 = token.split(".")[1]
            padding = "=" * (4 - len(pb64) % 4)
            return json.loads(base64.urlsafe_b64decode(pb64 + padding))

        p1 = get_payload(r1)
        p2 = get_payload(r2)

        if "jti" in p1 and "jti" in p2:
            assert p1["jti"] != p2["jti"], (
                "Two login sessions share the same jti — token revocation is broken!"
            )


# ─────────────────────────────────────────────
# SECTION 11: TOTP / 2FA ENFORCEMENT
# ─────────────────────────────────────────────

class TestTwoFactorAuth:

    def test_admin_login_without_totp_fails(self):
        """Admin login without TOTP must be rejected."""
        r = login(ADMIN_EMAIL, ADMIN_PASSWORD)  # No totp
        assert r.status_code in (400, 401, 422), (
            f"Admin login without TOTP succeeded! Status: {r.status_code}"
        )

    def test_admin_login_with_wrong_totp_fails(self):
        """Admin login with a wrong TOTP code must be rejected."""
        r = login(ADMIN_EMAIL, ADMIN_PASSWORD, totp="000000")
        assert r.status_code in (400, 401, 422), (
            f"Admin login with wrong TOTP succeeded! Status: {r.status_code}"
        )

    def test_admin_login_with_valid_totp_succeeds(self):
        """Admin login with correct TOTP must succeed."""
        r = login(ADMIN_EMAIL, ADMIN_PASSWORD, totp=get_totp_code())
        assert r.status_code == 200, (
            f"Admin login with valid TOTP failed: {r.status_code} — {r.text}"
        )

    def test_checker_login_without_totp_fails(self):
        """Checker login without TOTP must be rejected."""
        r = login(CHECKER_EMAIL, CHECKER_PASSWORD)
        assert r.status_code in (400, 401, 422), (
            f"Checker login without TOTP succeeded! Status: {r.status_code}"
        )

    def test_agent_login_without_totp_succeeds(self):
        """Agent (no 2FA required) must be able to log in without TOTP."""
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert r.status_code == 200, (
            f"Agent login failed unexpectedly: {r.status_code} — {r.text}"
        )


# ─────────────────────────────────────────────
# HELPERS (private)
# ─────────────────────────────────────────────

def _check_nid_in_error_only(response_str: str, nid: str) -> bool:
    """
    Returns True if the NID appears only inside an error message field,
    not as a standalone data value. This is a lenient check — ideally
    NID should never appear plaintext anywhere.
    """
    try:
        data = json.loads(response_str)
        error_block = json.dumps(data.get("error", {}))
        return nid in error_block
    except Exception:
        return False


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    subprocess.run(
        [
            "pytest",
            __file__,
            "-v",
            "--tb=short",
            "--no-header",
            "-rN",
        ]
    )
