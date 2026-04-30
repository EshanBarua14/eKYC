"""
Tests for Sentry integration — BFIU §4.5 production observability.
Verifies: init with no DSN is safe, PII masking works, import succeeds.
"""
import pytest
from app.core.sentry import init_sentry, _before_send


def test_sentry_init_no_dsn_returns_false():
    """init_sentry with empty DSN must return False — not crash."""
    result = init_sentry(dsn="", environment="test", release="1.0.0")
    assert result is False


def test_sentry_init_invalid_dsn_returns_false():
    """init_sentry with garbage DSN must not crash startup."""
    result = init_sentry(dsn="not-a-real-dsn", environment="test", release="1.0.0")
    assert result is False


def test_before_send_strips_request_body():
    """Request body (biometric base64) must be removed before sending to Sentry."""
    event = {
        "request": {
            "url": "/api/v1/face/verify",
            "method": "POST",
            "data": {"live_image_b64": "data:image/jpeg;base64,BIOMETRIC_DATA"},
            "body": "raw body",
            "headers": {"Authorization": "Bearer secret-token"},
        }
    }
    result = _before_send(event, {})
    assert "data" not in result["request"]
    assert "body" not in result["request"]
    assert "Authorization" not in result["request"]["headers"]


def test_before_send_masks_nid_in_breadcrumbs():
    """NID numbers (10-17 digits) must be masked in breadcrumbs."""
    event = {
        "breadcrumbs": {
            "values": [{"message": "Processing NID 1234567890123456"}]
        }
    }
    result = _before_send(event, {})
    msg = result["breadcrumbs"]["values"][0]["message"]
    assert "1234567890123456" not in msg
    assert "***NID***" in msg


def test_before_send_no_crash_on_minimal_event():
    """_before_send must not crash on minimal event with no request."""
    event = {"exception": {"values": [{"type": "ValueError", "value": "test"}]}}
    result = _before_send(event, {})
    assert result is not None


def test_sentry_module_importable():
    """sentry.py must be importable without errors."""
    from app.core import sentry
    assert hasattr(sentry, "init_sentry")
    assert hasattr(sentry, "_before_send")
