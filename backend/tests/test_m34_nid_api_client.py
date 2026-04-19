"""
M34 — EC NID API Client Tests
HTTP client with retry/backoff, pending_verification state, Celery retry queue.
"""
import pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════════════════════════
# 1. lookup_nid — DEMO mode
# ══════════════════════════════════════════════════════════════════════════
class TestLookupNIDDemo:
    def test_known_nid_returns_found(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("1234567890123", mode="DEMO")
        assert result["found"] is True

    def test_known_nid_returns_verified_status(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("1234567890123", mode="DEMO")
        assert result["status"] == "verified"

    def test_known_nid_has_data(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("1234567890123", mode="DEMO")
        assert result["data"] is not None
        assert result["data"]["full_name_en"] == "RAHMAN HOSSAIN CHOWDHURY"

    def test_unknown_nid_returns_not_found(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("0000000000000", mode="DEMO")
        assert result["found"] is False

    def test_unknown_nid_returns_not_found_status(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("0000000000000", mode="DEMO")
        assert result["status"] == "not_found"

    def test_result_has_timestamp(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("1234567890123", mode="DEMO")
        assert "timestamp" in result

    def test_result_has_source(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("1234567890123", mode="DEMO")
        assert result["source"] == "DEMO"

    def test_second_known_nid(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("9876543210987", mode="DEMO")
        assert result["found"] is True
        assert result["data"]["full_name_en"] == "FATEMA BEGUM"

    def test_third_known_nid(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("1111111111111", mode="DEMO")
        assert result["found"] is True


# ══════════════════════════════════════════════════════════════════════════
# 2. lookup_nid — STUB mode
# ══════════════════════════════════════════════════════════════════════════
class TestLookupNIDStub:
    def test_stub_always_returns_found(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("9999999999999", mode="STUB")
        assert result["found"] is True

    def test_stub_returns_verified_status(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("9999999999999", mode="STUB")
        assert result["status"] == "verified"

    def test_stub_source_is_stub(self):
        from app.services.nid_api_client import lookup_nid
        result = lookup_nid("9999999999999", mode="STUB")
        assert result["source"] == "STUB"


# ══════════════════════════════════════════════════════════════════════════
# 3. lookup_nid_with_retry
# ══════════════════════════════════════════════════════════════════════════
class TestLookupNIDWithRetry:
    def test_success_on_first_attempt(self):
        from app.services.nid_api_client import lookup_nid_with_retry
        result = lookup_nid_with_retry(
            "1234567890123", session_id="sess_r01", enqueue_on_failure=False
        )
        assert result["found"] is True
        assert result["status"] == "verified"

    def test_not_found_nid_returns_not_found(self):
        from app.services.nid_api_client import lookup_nid_with_retry
        result = lookup_nid_with_retry(
            "0000000000000", session_id="sess_r02", enqueue_on_failure=False
        )
        assert result["found"] is False

    def test_ec_unavailable_returns_pending_verification(self):
        from app.services.nid_api_client import lookup_nid_with_retry, EC_UNAVAILABLE
        ec_down = {
            "found": False, "status": EC_UNAVAILABLE,
            "error_code": EC_UNAVAILABLE, "source": "LIVE",
            "timestamp": "2026-04-20T00:00:00+00:00",
        }
        with patch("app.services.nid_api_client.lookup_nid", return_value=ec_down):
            with patch("app.services.nid_api_client._enqueue_async_retry"):
                result = lookup_nid_with_retry(
                    "1234567890123", "sess_r03",
                    enqueue_on_failure=True
                )
        assert result["status"] == "pending_verification"

    def test_ec_unavailable_enqueues_celery_task(self):
        from app.services.nid_api_client import lookup_nid_with_retry, EC_UNAVAILABLE
        ec_down = {
            "found": False, "status": EC_UNAVAILABLE,
            "error_code": EC_UNAVAILABLE, "source": "LIVE",
            "timestamp": "2026-04-20T00:00:00+00:00",
        }
        with patch("app.services.nid_api_client.lookup_nid", return_value=ec_down):
            with patch("app.services.nid_api_client._enqueue_async_retry") as mock_enqueue:
                lookup_nid_with_retry("1234567890123", "sess_r04", enqueue_on_failure=True)
        mock_enqueue.assert_called_once()

    def test_ec_unavailable_no_enqueue_when_disabled(self):
        from app.services.nid_api_client import lookup_nid_with_retry, EC_UNAVAILABLE
        ec_down = {
            "found": False, "status": EC_UNAVAILABLE,
            "error_code": EC_UNAVAILABLE, "source": "LIVE",
            "timestamp": "2026-04-20T00:00:00+00:00",
        }
        with patch("app.services.nid_api_client.lookup_nid", return_value=ec_down):
            with patch("app.services.nid_api_client._enqueue_async_retry") as mock_enqueue:
                lookup_nid_with_retry(
                    "1234567890123", "sess_r05", enqueue_on_failure=False
                )
        mock_enqueue.assert_not_called()

    def test_pending_verification_has_session_id(self):
        from app.services.nid_api_client import lookup_nid_with_retry, EC_UNAVAILABLE
        ec_down = {
            "found": False, "status": EC_UNAVAILABLE,
            "error_code": EC_UNAVAILABLE, "source": "LIVE",
            "timestamp": "2026-04-20T00:00:00+00:00",
        }
        with patch("app.services.nid_api_client.lookup_nid", return_value=ec_down):
            with patch("app.services.nid_api_client._enqueue_async_retry"):
                result = lookup_nid_with_retry("1234567890123", "sess_r06")
        assert result.get("session_id") == "sess_r06"


# ══════════════════════════════════════════════════════════════════════════
# 4. cross_match_nid
# ══════════════════════════════════════════════════════════════════════════
class TestCrossMatchNID:
    def test_exact_name_and_dob_match(self):
        from app.services.nid_api_client import cross_match_nid
        ocr = {"full_name_en": "RAHMAN HOSSAIN CHOWDHURY", "date_of_birth": "1990-01-15"}
        ec  = {"full_name_en": "RAHMAN HOSSAIN CHOWDHURY", "date_of_birth": "1990-01-15"}
        result = cross_match_nid(ocr, ec)
        assert result["match"] is True
        assert result["score_pct"] == 100.0

    def test_no_ec_record_returns_no_match(self):
        from app.services.nid_api_client import cross_match_nid
        result = cross_match_nid({"full_name_en": "TEST"}, None)
        assert result["match"] is False

    def test_wrong_dob_reduces_score(self):
        from app.services.nid_api_client import cross_match_nid
        ocr = {"full_name_en": "RAHMAN HOSSAIN CHOWDHURY", "date_of_birth": "1991-01-15"}
        ec  = {"full_name_en": "RAHMAN HOSSAIN CHOWDHURY", "date_of_birth": "1990-01-15"}
        result = cross_match_nid(ocr, ec)
        assert result["score_pct"] < 100.0

    def test_completely_different_names_no_match(self):
        from app.services.nid_api_client import cross_match_nid
        ocr = {"full_name_en": "JOHN SMITH", "date_of_birth": "1990-01-15"}
        ec  = {"full_name_en": "FATEMA BEGUM", "date_of_birth": "1985-06-20"}
        result = cross_match_nid(ocr, ec)
        assert result["match"] is False

    def test_result_has_fields_checked(self):
        from app.services.nid_api_client import cross_match_nid
        ocr = {"full_name_en": "RAHMAN HOSSAIN", "date_of_birth": "1990-01-15"}
        ec  = {"full_name_en": "RAHMAN HOSSAIN", "date_of_birth": "1990-01-15"}
        result = cross_match_nid(ocr, ec)
        assert result["fields_checked"] == 2


# ══════════════════════════════════════════════════════════════════════════
# 5. EC error codes
# ══════════════════════════════════════════════════════════════════════════
class TestECErrorCodes:
    def test_error_codes_defined(self):
        from app.services.nid_api_client import (
            EC_UNAVAILABLE, EC_RATE_LIMITED, EC_AUTH_ERROR,
            EC_NOT_FOUND, EC_SERVER_ERROR
        )
        assert EC_UNAVAILABLE  == "EC_UNAVAILABLE"
        assert EC_RATE_LIMITED == "EC_RATE_LIMITED"
        assert EC_AUTH_ERROR   == "EC_AUTH_ERROR"
        assert EC_NOT_FOUND    == "EC_NOT_FOUND"
        assert EC_SERVER_ERROR == "EC_SERVER_ERROR"

    def test_live_lookup_connection_error_returns_ec_unavailable(self):
        from app.services.nid_api_client import _live_lookup
        with patch("requests.Session.post", side_effect=ConnectionError("timeout")):
            result = _live_lookup("1234567890123")
        assert result["error_code"] == "EC_UNAVAILABLE"
        assert result["status"] == "EC_UNAVAILABLE"

    def test_live_lookup_404_returns_not_found(self):
        from app.services.nid_api_client import _live_lookup
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("requests.Session.post", return_value=mock_resp):
            result = _live_lookup("1234567890123")
        assert result["error_code"] == "EC_NOT_FOUND"

    def test_live_lookup_429_returns_rate_limited(self):
        from app.services.nid_api_client import _live_lookup
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        with patch("requests.Session.post", return_value=mock_resp):
            result = _live_lookup("1234567890123")
        assert result["error_code"] == "EC_RATE_LIMITED"

    def test_live_lookup_401_returns_auth_error(self):
        from app.services.nid_api_client import _live_lookup
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("requests.Session.post", return_value=mock_resp):
            result = _live_lookup("1234567890123")
        assert result["error_code"] == "EC_AUTH_ERROR"
