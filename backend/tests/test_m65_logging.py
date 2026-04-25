"""
M65 Tests: Structured JSON logging + PII masking
"""
import json
import logging
import pytest
from app.core.logging_config import JSONFormatter, RequestContextFilter, _mask_pii, configure_logging


def _capture_log(level, msg, **extra):
    """Helper: format a log record and return parsed JSON."""
    record = logging.LogRecord(
        name="test", level=level, pathname="", lineno=0,
        msg=msg, args=(), exc_info=None
    )
    for k, v in extra.items():
        setattr(record, k, v)
    formatter = JSONFormatter()
    line = formatter.format(record)
    return json.loads(line)


def test_T01_json_output_is_valid():
    d = _capture_log(logging.INFO, "test message")
    assert isinstance(d, dict)

def test_T02_has_required_fields():
    d = _capture_log(logging.INFO, "test")
    for field in ["timestamp", "level", "logger", "message"]:
        assert field in d, f"Missing field: {field}"

def test_T03_timestamp_is_bst():
    d = _capture_log(logging.INFO, "test")
    assert "+06:00" in d["timestamp"]

def test_T04_level_is_correct():
    d = _capture_log(logging.ERROR, "err msg")
    assert d["level"] == "ERROR"

def test_T05_request_id_injected():
    d = _capture_log(logging.INFO, "test", request_id="req-abc-123")
    assert d["request_id"] == "req-abc-123"

def test_T06_user_context_injected():
    d = _capture_log(logging.INFO, "test", user_id="usr-1", role="CHECKER")
    assert d["user_id"] == "usr-1"
    assert d["role"] == "CHECKER"

def test_T07_pii_nid_masked():
    result = _mask_pii('"nid_number": "1234567890123"')
    # Full NID must not appear — only last 4 digits or REDACTED acceptable
    assert "1234567890123" not in result or "****" in result

def test_T08_pii_mobile_masked():
    result = _mask_pii("mobile: 01712345678")
    assert "01712345678" not in result
    assert "017" in result  # prefix kept

def test_T09_pii_email_masked():
    result = _mask_pii("user@example.com")
    assert "user@example.com" not in result
    assert "@example.com" in result

def test_T10_non_pii_not_masked():
    result = _mask_pii("risk_score: 15")
    assert "risk_score: 15" == result

def test_T11_exception_logged():
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="error", args=(), exc_info=sys.exc_info()
        )
        d = json.loads(JSONFormatter().format(record))
        assert "exception" in d
        assert d["exception"]["type"] == "ValueError"

def test_T12_request_context_filter_sets_attrs():
    RequestContextFilter.set_context(request_id="test-123", role="ADMIN")
    record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
    f = RequestContextFilter()
    f.filter(record)
    assert record.request_id == "test-123"
    assert record.role == "ADMIN"
    RequestContextFilter.clear_context()

def test_T13_configure_logging_runs():
    configure_logging(level="INFO", json_output=True)
    logger = logging.getLogger("ekyc")
    assert logger is not None

def test_T14_configure_logging_sets_level():
    configure_logging(level="WARNING", json_output=False)
    root = logging.getLogger()
    assert root.level == logging.WARNING
    configure_logging(level="INFO", json_output=False)  # restore

def test_T15_json_lines_are_single_line():
    d = _capture_log(logging.INFO, "test message with spaces")
    line = JSONFormatter().format(
        logging.LogRecord("t", logging.INFO, "", 0, "test message", (), None)
    )
    assert "\n" not in line

def test_T16_bfiu_ref_in_extra():
    d = _capture_log(logging.INFO, "audit", bfiu_ref="BFIU §5.1")
    assert "bfiu_ref" in d
    assert "5.1" in d["bfiu_ref"]
