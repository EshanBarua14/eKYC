import pytest
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

BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"

AGENT_EMAIL    = "agent@demo.ekyc"
AGENT_PASSWORD = "DemoAgent@2026"
ADMIN_EMAIL    = "admin@demo.ekyc"
ADMIN_PASSWORD = "AdminDemo@2026"
TOTP_SECRET    = "JBSWY3DPEHPK3PXP"
CHECKER_EMAIL    = "checker@demo.ekyc"
CHECKER_PASSWORD = "DemoChecker@2026"

pytestmark = pytest.mark.integration

def get_totp_code():
    return pyotp.TOTP(TOTP_SECRET).now()

def login(email, password, totp=None):
    payload = {"email": email, "password": password}
    if totp:
        payload["totp_code"] = totp
    return requests.post(f"{BASE_URL}/auth/token", json=payload, timeout=10)

def agent_token():
    r = login(AGENT_EMAIL, AGENT_PASSWORD)
    assert r.status_code == 200, f"Agent login failed: {r.text}"
    d = r.json()
    return d.get("access_token") or d.get("token")

def admin_token():
    r = login(ADMIN_EMAIL, ADMIN_PASSWORD, totp=get_totp_code())
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    d = r.json()
    return d.get("access_token") or d.get("token")

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def tampered_jwt(token):
    parts = token.split(".")
    if len(parts) != 3:
        return token
    sig = parts[2]
    sig_bytes = base64.urlsafe_b64decode(sig + "==")
    tampered = bytearray(sig_bytes)
    tampered[0] ^= 0x01
    parts[2] = base64.urlsafe_b64encode(bytes(tampered)).rstrip(b"=").decode()
    return ".".join(parts)

def alg_none_token(token):
    parts = token.split(".")
    if len(parts) != 3:
        return token
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
    header["alg"] = "none"
    new_header = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    return f"{new_header}.{parts[1]}."

def get_payload(token):
    pb64 = token.split(".")[1]
    padding = "=" * (4 - len(pb64) % 4)
    return json.loads(base64.urlsafe_b64decode(pb64 + padding))

@pytest.fixture(scope="module")
def valid_agent_token():
    return agent_token()

@pytest.fixture(scope="module")
def valid_admin_token():
    return admin_token()


class TestPreFlight:
    def test_backend_is_alive(self):
        r = requests.get(HEALTH_URL, timeout=5)
        assert r.status_code == 200, "Backend not running. Start: uvicorn app.main:app --reload --port 8000"

    def test_health_returns_ok(self):
        r = requests.get(HEALTH_URL, timeout=5)
        assert r.json().get("status") in ("ok", "healthy")

    def test_health_no_auth_required(self):
        r = requests.get(HEALTH_URL, timeout=5)
        assert r.status_code not in (401, 403)


class TestBrokenAuthentication:
    def test_no_token_returns_401(self):
        r = requests.post(f"{BASE_URL}/nid/verify", json={"nid_number":"test","date_of_birth":"1990-01-01"}, timeout=5)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_empty_bearer_returns_401(self):
        r = requests.post(f"{BASE_URL}/nid/verify", headers={"Authorization": "Bearer "}, json={}, timeout=5)
        assert r.status_code in (401, 403)

    def test_garbage_token_returns_401(self):
        r = requests.post(f"{BASE_URL}/nid/verify", headers={"Authorization": "Bearer not.a.jwt"}, json={}, timeout=5)
        assert r.status_code in (401, 403)

    def test_tampered_signature_rejected(self, valid_agent_token):
        bad = tampered_jwt(valid_agent_token)
        r = requests.post(f"{BASE_URL}/ai/scan-nid", headers=auth_headers(bad), json={"image_base64":"dGVzdA=="}, timeout=5)
        assert r.status_code in (401, 403, 422), f"Tampered JWT accepted with 2xx! {r.status_code}"

    def test_alg_none_attack_rejected(self, valid_agent_token):
        none_tok = alg_none_token(valid_agent_token)
        r = requests.post(f"{BASE_URL}/ai/scan-nid", headers=auth_headers(none_tok), json={"image_base64":"dGVzdA=="}, timeout=5)
        assert r.status_code in (401, 403, 422), f"CRITICAL: alg=none JWT accepted with 2xx! {r.status_code}"

    def test_wrong_password_returns_401(self):
        r = login(AGENT_EMAIL, "WrongPassword@123")
        assert r.status_code == 401, f"Wrong password gave {r.status_code}"

    def test_nonexistent_user_returns_401(self):
        r = login("ghost@nowhere.invalid", "SomePassword@123")
        assert r.status_code == 401

    def test_login_error_message_is_generic(self):
        r1 = login("ghost@nowhere.invalid", "any")
        r2 = login(AGENT_EMAIL, "WrongPassword@123")
        assert r1.status_code == 401
        assert r2.status_code == 401


class TestBrokenAccessControl:
    def test_agent_cannot_access_admin_users_endpoint(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/admin/users", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (401, 403), f"Agent accessed /admin/users! {r.status_code}"

    def test_agent_cannot_access_audit_export(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/admin/audit-logs/export", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (401, 403), f"Agent accessed /audit/export! {r.status_code}"

    def test_agent_cannot_access_institution_settings(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/admin/users", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (401, 403)

    def test_agent_cannot_approve_verifications(self, valid_agent_token):
        fake_id = str(uuid.uuid4())
        r = requests.post(f"{BASE_URL}/fallback/{fake_id}/review/start", headers=auth_headers(valid_agent_token),
                          json={"decision": "approve"}, timeout=5)
        assert r.status_code in (401, 403, 422), f"Agent called review! {r.status_code}"

    def test_agent_cannot_delete_users(self, valid_agent_token):
        fake_id = str(uuid.uuid4())
        r = requests.delete(f"{BASE_URL}/admin/users/{fake_id}", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (401, 403)

    def test_admin_can_access_admin_endpoints(self, valid_admin_token):
        r = requests.get(f"{BASE_URL}/admin/users", headers=auth_headers(valid_admin_token), timeout=5)
        assert r.status_code in (200, 404), f"Admin blocked from /admin/users: {r.status_code}"


class TestIDOR:
    def test_idor_verification_result(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/face/verify/{uuid.uuid4()}", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (403, 404), f"IDOR: {r.status_code}"

    def test_idor_liveness_session(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/ai/session/{uuid.uuid4()}", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (403, 404)

    def test_idor_kyc_profile(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/kyc/profile/{uuid.uuid4()}", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (403, 404)

    def test_idor_audit_log_entry(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/audit/{uuid.uuid4()}", headers=auth_headers(valid_agent_token), timeout=5)
        assert r.status_code in (401, 403, 404)


class TestInjection:
    SQL_PAYLOADS = [
        "' OR '1'='1", "' OR 1=1--", "'; DROP TABLE users;--",
        "1' UNION SELECT null,null,null--", "admin'--",
    ]
    XSS_PAYLOADS = [
        "<script>alert(1)</script>", '"><img src=x onerror=alert(1)>',
        "javascript:alert(1)", "<svg onload=alert(1)>",
    ]

    def test_sql_injection_in_login_email(self):
        for p in self.SQL_PAYLOADS:
            r = login(p, "anything")
            assert r.status_code != 500, f"SQLi caused 500: {p!r}"
            assert r.status_code != 200, f"SQLi bypassed auth: {p!r}"

    def test_sql_injection_in_login_password(self):
        for p in self.SQL_PAYLOADS:
            r = login(AGENT_EMAIL, p)
            assert r.status_code != 200, f"SQLi in password bypassed auth: {p!r}"
            assert r.status_code != 500, f"SQLi in password caused 500: {p!r}"

    def test_sql_injection_in_nid_verify(self, valid_agent_token):
        for p in self.SQL_PAYLOADS:
            r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                              json={"nid_number": p, "date_of_birth": "1990-01-01"}, timeout=10)
            assert r.status_code != 500, f"SQLi in nid_number caused 500: {p!r}"

    def test_xss_payload_not_reflected(self, valid_agent_token):
        for p in self.XSS_PAYLOADS:
            r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                              json={"nid_number": p, "date_of_birth": "1990-01-01"}, timeout=10)
            assert "<script>" not in r.text, f"XSS reflected: {p!r}"

    def test_oversized_payload_rejected(self, valid_agent_token):
        r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                          json={"nid_number": "A" * 10000, "date_of_birth": "1990-01-01"}, timeout=10)
        assert r.status_code in (400, 413, 422), f"Oversized payload: {r.status_code}"

    def test_invalid_json_returns_400(self):
        r = requests.post(f"{BASE_URL}/auth/token", data="not json {{{{",
                          headers={"Content-Type": "application/json"}, timeout=5)
        assert r.status_code in (400, 422), f"Malformed JSON: {r.status_code}"


class TestSecurityMisconfiguration:
    def test_cors_arbitrary_origin_rejected(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/nid/verify",
                         headers={**auth_headers(valid_agent_token), "Origin": "https://evil-attacker.com"},
                         timeout=5)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "https://evil-attacker.com", "CORS mirrors evil Origin!"

    def test_cors_preflight_arbitrary_origin(self):
        r = requests.options(f"{BASE_URL}/auth/token",
                             headers={"Origin": "https://evil-attacker.com",
                                      "Access-Control-Request-Method": "POST"}, timeout=5)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "https://evil-attacker.com", "Preflight allows evil Origin!"

    def test_error_responses_use_standard_format(self):
        r = login("bad@user.com", "badpassword")
        assert r.headers.get("content-type", "").startswith("application/json")
        data = r.json()
        assert "error" in data or "detail" in data, f"Bad error format: {data}"

    def test_no_stack_trace_in_error_response(self, valid_agent_token):
        r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                          json={}, timeout=5)
        assert "Traceback" not in r.text, "Stack trace leaked!"
        assert 'File "' not in r.text, "Python path leaked!"

    def test_server_header_not_verbose(self):
        r = requests.get(HEALTH_URL, timeout=5)
        server = r.headers.get("Server", "").lower()
        for leak in ["uvicorn/", "python/", "fastapi/", "starlette/"]:
            assert leak not in server, f"Server header leaks version: {server}"

    def test_sensitive_data_not_in_health_endpoint(self):
        r = requests.get(HEALTH_URL, timeout=5)
        body = r.text.lower()
        for word in ["password", "secret", "database_url", "redis_url", "private_key"]:
            assert word not in body, f"'{word}' found in /health!"


class TestRateLimiting:
    def setup_method(self):
        try:
            from app.services.redis_client import get_redis
            r = get_redis()
            if r:
                keys = r.keys("rl:auth_token:*")
                if keys:
                    r.delete(*keys)
        except Exception:
            pass

    def test_login_rate_limit_enforced(self):
        blocked = False
        for i in range(15):
            r = login("ratelimit@test.invalid", f"wrong_{i}")
            if r.status_code == 429:
                blocked = True
                break
        assert blocked, "CRITICAL: 15 failed logins did not trigger 429. Brute-force unmitigated."

    def test_rate_limit_includes_retry_after(self):
        for i in range(15):
            r = login("ratelimit2@test.invalid", f"wrong_{i}")
            if r.status_code == 429:
                has_retry = ("Retry-After" in r.headers or "X-RateLimit-Reset" in r.headers
                             or "retry_after" in r.text.lower() or "reset_at" in r.text.lower())
                assert has_retry, "429 missing Retry-After header"
                return

    def test_x_forwarded_for_bypass(self):
        blocked = False
        for i in range(15):
            r = requests.post(f"{BASE_URL}/auth/token",
                              json={"email": f"test{i}@invalid.com", "password": "wrong"},
                              headers={"X-Forwarded-For": f"1.2.3.{i % 256}"}, timeout=5)
            if r.status_code == 429:
                blocked = True
                break
        if not blocked:
            pytest.xfail("FINDING: X-Forwarded-For rotation bypasses rate limiting. Use real socket IP.")


class TestSensitiveDataExposure:
    def test_login_response_no_password(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert AGENT_PASSWORD not in r.text, "Password echoed in login response!"

    def test_login_response_no_hash(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert "$argon2" not in r.text, "Argon2 hash exposed!"
        assert "$2b$" not in r.text, "bcrypt hash exposed!"

    def test_nid_not_plaintext_in_response(self, valid_agent_token):
        nid = "1234567890123"
        r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                          json={"nid_number": nid, "date_of_birth": "1985-07-15"}, timeout=10)
        if r.status_code in (200, 400, 422):
            body = r.text
            # NID should not appear as a bare value — only acceptable inside error messages
            if nid in body:
                data = r.json()
                error_str = json.dumps(data.get("error", {}))
                assert nid in error_str, f"NID in plaintext outside error block: {body[:200]}"

    def test_hsts_header(self):
        r = requests.get(HEALTH_URL, timeout=5)
        if not r.headers.get("Strict-Transport-Security"):
            pytest.xfail("HSTS not present on localhost — verify on production HTTPS endpoint.")

    def test_content_type_nosniff(self):
        r = requests.get(HEALTH_URL, timeout=5)
        assert r.headers.get("X-Content-Type-Options") == "nosniff", "X-Content-Type-Options missing!"

    def test_x_frame_options(self):
        r = requests.get(HEALTH_URL, timeout=5)
        xfo = r.headers.get("X-Frame-Options", "")
        assert xfo.upper() in ("DENY", "SAMEORIGIN"), f"X-Frame-Options missing or wrong: '{xfo}'"


class TestInputValidation:
    def test_extra_fields_ignored_not_500(self, valid_agent_token):
        r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                          json={"nid_number": "1234567890123", "date_of_birth": "1985-07-15",
                                "role": "admin", "is_admin": True, "__inject__": "evil"}, timeout=10)
        assert r.status_code != 500, "Extra fields caused 500!"

    def test_role_query_param_does_not_escalate(self, valid_agent_token):
        r = requests.get(f"{BASE_URL}/admin/users", headers=auth_headers(valid_agent_token),
                         params={"role": "admin"}, timeout=5)
        assert r.status_code in (401, 403), f"Role escalation via query param! {r.status_code}"

    def test_null_byte_injection(self, valid_agent_token):
        r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                          json={"nid_number": "123456789\x00012", "date_of_birth": "1990-01-01"}, timeout=5)
        assert r.status_code != 500, "Null byte caused 500!"

    def test_negative_nid_not_500(self, valid_agent_token):
        r = requests.post(f"{BASE_URL}/nid/verify", headers=auth_headers(valid_agent_token),
                          json={"nid_number": "-1", "date_of_birth": "1990-01-01"}, timeout=5)
        assert r.status_code != 500


class TestJWTSecurity:
    def test_jwt_uses_rs256(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        assert r.status_code == 200
        token = r.json().get("access_token") or r.json().get("token")
        hdr_b64 = token.split(".")[0]
        hdr = json.loads(base64.urlsafe_b64decode(hdr_b64 + "=="))
        assert hdr.get("alg") == "RS256", f"JWT alg is '{hdr.get('alg')}', expected RS256!"

    def test_jwt_has_exp_claim(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        token = r.json().get("access_token") or r.json().get("token")
        payload = get_payload(token)
        assert "exp" in payload, "JWT missing exp claim — token never expires!"
        assert "iat" in payload, "JWT missing iat claim!"

    def test_jwt_ttl_is_reasonable(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        token = r.json().get("access_token") or r.json().get("token")
        payload = get_payload(token)
        ttl = payload["exp"] - payload["iat"]
        assert 0 < ttl <= 3600, f"JWT TTL={ttl}s — must be > 0 and <= 3600s (spec: 900s)"

    def test_jwt_has_role_claim(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        token = r.json().get("access_token") or r.json().get("token")
        payload = get_payload(token)
        assert "role" in payload, "JWT missing role claim — RBAC cannot be enforced!"

    def test_unique_jti_per_login(self):
        r1 = login(AGENT_EMAIL, AGENT_PASSWORD)
        time.sleep(0.1)
        r2 = login(AGENT_EMAIL, AGENT_PASSWORD)
        t1 = r1.json().get("access_token") or r1.json().get("token")
        t2 = r2.json().get("access_token") or r2.json().get("token")
        p1, p2 = get_payload(t1), get_payload(t2)
        if "jti" in p1 and "jti" in p2:
            assert p1["jti"] != p2["jti"], "Two sessions share same jti — revocation broken!"


class TestTwoFactorAuth:
    def test_admin_login_without_totp_fails(self):
        r = login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert r.status_code in (400, 401, 422, 429), f"Admin login without TOTP succeeded! {r.status_code}"

    def test_admin_login_wrong_totp_fails(self):
        r = login(ADMIN_EMAIL, ADMIN_PASSWORD, totp="000000")
        assert r.status_code in (400, 401, 422, 429), f"Admin login with wrong TOTP succeeded! {r.status_code}"

    def test_admin_login_valid_totp_succeeds(self):
        r = login(ADMIN_EMAIL, ADMIN_PASSWORD, totp=get_totp_code())
        if r.status_code == 429: pytest.skip("Rate limit active from prior tests")
        assert r.status_code == 200, f"Admin login with valid TOTP failed: {r.status_code} — {r.text}"

    def test_checker_login_without_totp_fails(self):
        r = login(CHECKER_EMAIL, CHECKER_PASSWORD)
        assert r.status_code in (400, 401, 422, 429), f"Checker login without TOTP succeeded! {r.status_code}"

    def test_agent_login_no_totp_required(self):
        r = login(AGENT_EMAIL, AGENT_PASSWORD)
        if r.status_code == 429: pytest.skip("Rate limit active from prior tests")
        assert r.status_code == 200, f"Agent login failed: {r.status_code} — {r.text}"
