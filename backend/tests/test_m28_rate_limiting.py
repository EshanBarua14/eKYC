"""
test_m28_rate_limiting.py - M28 Rate Limiting
Tests: config, check, enforce, reset, stats, 429 response, BFIU limits
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.rate_limiter import reset_counters, RATE_LIMITS

client = TestClient(app)
BASE   = "/api/v1/rate-limits"


def setup_function():
    """Reset all counters before each test function."""
    reset_counters()


# ══════════════════════════════════════════════════════════════════════════
# 1. Configuration (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestConfig:
    def setup_method(self):
        reset_counters()

    def test_list_rate_limits_200(self):
        r = client.get(BASE)
        assert r.status_code == 200

    def test_list_has_bfiu_ref(self):
        r = client.get(BASE)
        assert "bfiu_ref" in r.json()
        assert "BFIU" in r.json()["bfiu_ref"]

    def test_list_has_required_endpoints(self):
        r = client.get(BASE)
        limits = r.json()["rate_limits"]
        for ep in ["auth_token", "face_verify", "nid_scan", "default"]:
            assert ep in limits, f"Missing endpoint: {ep}"

    def test_auth_token_limit_is_10(self):
        r = client.get(BASE)
        assert r.json()["rate_limits"]["auth_token"]["requests"] == 10

    def test_face_verify_limit_is_30(self):
        r = client.get(BASE)
        assert r.json()["rate_limits"]["face_verify"]["requests"] == 30

    def test_nid_scan_limit_is_60(self):
        r = client.get(BASE)
        assert r.json()["rate_limits"]["nid_scan"]["requests"] == 60


# ══════════════════════════════════════════════════════════════════════════
# 2. Check endpoint (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestCheck:
    def setup_method(self):
        reset_counters()

    def test_check_200(self):
        r = client.post(f"{BASE}/check", json={"endpoint":"face_verify","client_key":"ip_001"})
        assert r.status_code == 200

    def test_check_returns_allowed(self):
        r = client.post(f"{BASE}/check", json={"endpoint":"face_verify","client_key":"ip_002"})
        assert r.json()["allowed"] is True

    def test_check_returns_remaining(self):
        r = client.post(f"{BASE}/check", json={"endpoint":"face_verify","client_key":"ip_003"})
        d = r.json()
        assert "remaining" in d
        assert d["remaining"] == RATE_LIMITS["face_verify"]["requests"] - 1

    def test_check_decrements_remaining(self):
        key = "ip_decr_01"
        client.post(f"{BASE}/check", json={"endpoint":"face_verify","client_key":key})
        r2 = client.post(f"{BASE}/check", json={"endpoint":"face_verify","client_key":key})
        assert r2.json()["remaining"] == RATE_LIMITS["face_verify"]["requests"] - 2

    def test_check_unknown_endpoint_400(self):
        r = client.post(f"{BASE}/check", json={"endpoint":"unknown_xyz","client_key":"ip_004"})
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# 3. Rate limit enforcement (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestEnforcement:
    def setup_method(self):
        reset_counters()

    def test_within_limit_allowed(self):
        key = "ip_enf_01"
        reset_counters("auth_token", key)
        limit = RATE_LIMITS["auth_token"]["requests"]
        for i in range(limit):
            r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
            assert r.status_code == 200, f"Request {i+1} should be allowed"

    def test_exceeding_limit_returns_429(self):
        key = "ip_enf_02"
        limit = RATE_LIMITS["auth_token"]["requests"]
        for _ in range(limit):
            client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        assert r.status_code == 429

    def test_429_has_error_code(self):
        key = "ip_enf_03"
        limit = RATE_LIMITS["auth_token"]["requests"]
        for _ in range(limit + 1):
            r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        assert r.json()["detail"]["error"] == "RATE_LIMIT_EXCEEDED"

    def test_429_has_reset_at(self):
        key = "ip_enf_04"
        limit = RATE_LIMITS["auth_token"]["requests"]
        for _ in range(limit + 1):
            r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        assert "reset_at" in r.json()["detail"]

    def test_different_clients_independent(self):
        limit = RATE_LIMITS["auth_token"]["requests"]
        # Exhaust limit for client A
        for _ in range(limit + 1):
            client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":"ip_A"})
        # Client B should still be allowed
        r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":"ip_B"})
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════
# 4. Reset (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestReset:
    def setup_method(self):
        reset_counters()

    def test_reset_200(self):
        r = client.post(f"{BASE}/reset", json={})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_reset_clears_counter(self):
        key = "ip_rst_01"
        limit = RATE_LIMITS["auth_token"]["requests"]
        for _ in range(limit + 1):
            client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        # Reset
        client.post(f"{BASE}/reset", json={"endpoint":"auth_token","client_key":key})
        # Should be allowed again
        r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        assert r.status_code == 200

    def test_reset_specific_endpoint(self):
        key = "ip_rst_02"
        limit = RATE_LIMITS["auth_token"]["requests"]
        for _ in range(limit + 1):
            client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        client.post(f"{BASE}/reset", json={"endpoint":"auth_token","client_key":key})
        r = client.post(f"{BASE}/check", json={"endpoint":"auth_token","client_key":key})
        assert r.json()["allowed"] is True


# ══════════════════════════════════════════════════════════════════════════
# 5. Stats (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestStats:
    def setup_method(self):
        reset_counters()

    def test_stats_200(self):
        r = client.get(f"{BASE}/stats")
        assert r.status_code == 200

    def test_stats_has_active_keys(self):
        r = client.get(f"{BASE}/stats")
        assert "active_keys" in r.json()

    def test_stats_increments_after_check(self):
        reset_counters()
        client.post(f"{BASE}/check", json={"endpoint":"face_verify","client_key":"ip_stat_01"})
        r = client.get(f"{BASE}/stats")
        assert r.json()["active_keys"] >= 1


# ══════════════════════════════════════════════════════════════════════════
# 6. Service unit tests (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestRateLimiterService:
    def setup_method(self):
        reset_counters()

    def test_check_returns_dict(self):
        from app.services.rate_limiter import check_rate_limit
        result = check_rate_limit("face_verify", "unit_test_ip")
        assert isinstance(result, dict)

    def test_first_request_always_allowed(self):
        from app.services.rate_limiter import check_rate_limit
        result = check_rate_limit("auth_token", "fresh_ip_001")
        assert result["allowed"] is True
        assert result["count"] == 1

    def test_remaining_decrements(self):
        from app.services.rate_limiter import check_rate_limit
        key = "unit_ip_002"
        r1 = check_rate_limit("face_verify", key)
        r2 = check_rate_limit("face_verify", key)
        assert r2["remaining"] == r1["remaining"] - 1

    def test_limit_matches_config(self):
        from app.services.rate_limiter import check_rate_limit
        result = check_rate_limit("auth_token", "unit_ip_003")
        assert result["limit"] == RATE_LIMITS["auth_token"]["requests"]

    def test_unknown_endpoint_uses_default(self):
        from app.services.rate_limiter import check_rate_limit
        result = check_rate_limit("unknown_endpoint", "unit_ip_004")
        assert result["limit"] == RATE_LIMITS["default"]["requests"]
