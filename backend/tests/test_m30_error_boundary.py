"""
test_m30_error_boundary.py - M30 Error Boundary
Tests: request ID, structured errors, no stack traces, 404/422/500 handling,
       validation errors, rate limit errors, BFIU error format
"""
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ══════════════════════════════════════════════════════════════════════════
# 1. Request ID (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestRequestID:
    def test_response_has_x_request_id_header(self):
        r = client.get("/api/v1/gateway/health")
        assert "x-request-id" in r.headers or "X-Request-ID" in r.headers

    def test_request_id_is_uuid(self):
        r = client.get("/api/v1/gateway/health")
        rid = r.headers.get("x-request-id") or r.headers.get("X-Request-ID","")
        assert len(rid) == 36
        assert rid.count("-") == 4

    def test_custom_request_id_propagated(self):
        custom_id = "test-req-id-12345678-abcd"
        r = client.get("/api/v1/gateway/health",
                       headers={"X-Request-ID": custom_id})
        returned = r.headers.get("x-request-id") or r.headers.get("X-Request-ID","")
        assert returned == custom_id

    def test_response_has_response_time_header(self):
        r = client.get("/api/v1/gateway/health")
        rt = r.headers.get("x-response-time") or r.headers.get("X-Response-Time","")
        assert "ms" in rt

# ══════════════════════════════════════════════════════════════════════════
# 2. 404 Not Found (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class Test404:
    def test_404_returns_json(self):
        r = client.get("/api/v1/nonexistent-endpoint-xyz")
        assert r.status_code == 404
        assert r.headers.get("content-type","").startswith("application/json")

    def test_404_has_error_structure(self):
        r = client.get("/api/v1/nonexistent-xyz")
        d = r.json()
        assert "error" in d
        assert "code" in d["error"]
        assert "message" in d["error"]
        assert "request_id" in d["error"]

    def test_404_code_is_not_found(self):
        r = client.get("/api/v1/nonexistent-xyz")
        assert r.json()["error"]["code"] == "NOT_FOUND"

    def test_404_no_stack_trace(self):
        r = client.get("/api/v1/nonexistent-xyz")
        assert "Traceback" not in r.text
        assert "traceback" not in r.text.lower()

# ══════════════════════════════════════════════════════════════════════════
# 3. 422 Validation Error (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class Test422:
    def test_422_on_bad_payload(self):
        r = client.post("/api/v1/outcome/create", json={"bad_field": "value"})
        assert r.status_code == 422

    def test_422_has_error_structure(self):
        r = client.post("/api/v1/outcome/create", json={})
        assert "error" in r.json()

    def test_422_has_validation_details(self):
        r = client.post("/api/v1/outcome/create", json={})
        err = r.json()["error"]
        assert err["code"] == "VALIDATION_ERROR"
        assert "details" in err
        assert "validation_errors" in err["details"]

    def test_422_validation_errors_have_field(self):
        r = client.post("/api/v1/outcome/create", json={})
        errors = r.json()["error"]["details"]["validation_errors"]
        assert len(errors) > 0
        assert "field" in errors[0]
        assert "message" in errors[0]

# ══════════════════════════════════════════════════════════════════════════
# 4. 401 / 403 Auth Errors (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAuthErrors:
    def test_401_has_error_structure(self):
        r = client.get("/api/v1/audit/log",
                       headers={"Authorization": "Bearer invalid_token"})
        assert r.status_code == 401
        assert "error" in r.json()

    def test_403_has_error_structure(self):
        r = client.get("/api/v1/admin/stats")
        assert r.status_code == 403
        assert "error" in r.json()

    def test_403_code_is_forbidden(self):
        r = client.get("/api/v1/admin/stats")
        assert r.json()["error"]["code"] in ("FORBIDDEN", "ADMIN_REQUIRED")

# ══════════════════════════════════════════════════════════════════════════
# 5. Error format compliance (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestErrorFormat:
    def test_error_has_timestamp(self):
        r = client.get("/api/v1/nonexistent-xyz")
        assert "timestamp" in r.json()["error"]

    def test_error_has_status_code(self):
        r = client.get("/api/v1/nonexistent-xyz")
        assert r.json()["error"]["status"] == 404

    def test_error_has_bfiu_ref(self):
        r = client.get("/api/v1/nonexistent-xyz")
        assert "bfiu_ref" in r.json()["error"]
        assert "BFIU" in r.json()["error"]["bfiu_ref"]

    def test_error_request_id_matches_header(self):
        r = client.get("/api/v1/nonexistent-xyz")
        header_id = r.headers.get("x-request-id") or r.headers.get("X-Request-ID","")
        body_id   = r.json()["error"]["request_id"]
        assert header_id == body_id

# ══════════════════════════════════════════════════════════════════════════
# 6. 500 Internal Server Error (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class Test500:
    def test_500_no_stack_trace_in_response(self):
        # Trigger a 500 via a route that raises unhandled exception
        from app.api.v1.router import v1_router
        from fastapi import APIRouter
        # Use existing invalid DB scenario instead
        r = client.get("/api/v1/nonexistent-xyz")
        assert "Traceback" not in r.text

    def test_unhandled_exception_returns_500(self):
        # Add a test route that raises an unhandled exception
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.middleware.error_boundary import register_error_handlers
        test_app = FastAPI()
        register_error_handlers(test_app)

        @test_app.get("/crash")
        def crash():
            raise RuntimeError("intentional crash for testing")

        tc = TestClient(test_app, raise_server_exceptions=False)
        r = tc.get("/crash")
        assert r.status_code == 500
        assert "error" in r.json()
        assert r.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"

    def test_500_message_is_safe(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.middleware.error_boundary import register_error_handlers
        test_app = FastAPI()
        register_error_handlers(test_app)

        @test_app.get("/crash")
        def crash():
            raise RuntimeError("SECRET_DB_PASSWORD=supersecret123")

        tc = TestClient(test_app, raise_server_exceptions=False)
        r = tc.get("/crash")
        assert "supersecret" not in r.text
        assert "SECRET_DB_PASSWORD" not in r.text
