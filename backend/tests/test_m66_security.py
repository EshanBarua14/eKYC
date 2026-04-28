"""
M66 Tests: CORS lock + Admin IP whitelist + alertmanager config
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient


# ── T01-T06: Admin IP whitelist ───────────────────────────────────────────
def test_T01_whitelist_empty_allows_all():
    from app.middleware.admin_ip_whitelist import _get_whitelist
    with patch.dict(os.environ, {"ADMIN_IP_WHITELIST": ""}):
        assert _get_whitelist() == []

def test_T02_whitelist_parses_ips():
    from app.middleware.admin_ip_whitelist import _get_whitelist
    with patch.dict(os.environ, {"ADMIN_IP_WHITELIST": "10.0.0.1,10.0.0.2"}):
        wl = _get_whitelist()
        assert "10.0.0.1" in wl
        assert "10.0.0.2" in wl

def test_T03_admin_path_detected():
    from app.middleware.admin_ip_whitelist import PROTECTED_PREFIXES
    assert "/api/v1/admin" in PROTECTED_PREFIXES
    assert "/api/v1/pep/entries" in PROTECTED_PREFIXES

def test_T04_non_admin_path_not_protected():
    from app.middleware.admin_ip_whitelist import PROTECTED_PREFIXES
    assert "/api/v1/kyc" not in PROTECTED_PREFIXES
    assert "/health" not in PROTECTED_PREFIXES

def test_T05_get_client_ip_from_forwarded():
    from app.middleware.admin_ip_whitelist import _get_client_ip
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
    req.client = None
    assert _get_client_ip(req) == "203.0.113.1"

def test_T06_get_client_ip_direct():
    from app.middleware.admin_ip_whitelist import _get_client_ip
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock()
    req.client.host = "192.168.1.1"
    assert _get_client_ip(req) == "192.168.1.1"


# ── T07-T10: CORS config ──────────────────────────────────────────────────
def test_T07_cors_origins_parsed():
    from app.core.config import Settings
    s = Settings(ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com")
    assert "https://app.example.com" in s.ALLOWED_ORIGINS_LIST

def test_T08_cors_localhost_warning_in_prod(caplog):
    """G29: prod startup must BLOCK if all origins are localhost — BFIU s4.5."""
    import logging
    from pydantic import ValidationError
    from app.core.config import Settings
    import secrets
    strong_key = secrets.token_hex(32)
    with patch.dict(os.environ, {"DEBUG": "false", "SECRET_KEY": strong_key}):
        with caplog.at_level(logging.WARNING):
            try:
                s = Settings(ALLOWED_ORIGINS="http://localhost:3000", SECRET_KEY=strong_key)
                raised = False
            except (ValueError, ValidationError):
                raised = True
    # G29: must crash OR strip localhost — either way localhost must not reach prod
    assert raised or "http://localhost:3000" not in s.ALLOWED_ORIGINS_LIST

def test_T09_cors_localhost_ok_in_dev():
    from app.core.config import Settings
    with patch.dict(os.environ, {"DEBUG": "true"}):
        s = Settings(ALLOWED_ORIGINS="http://localhost:3000")
        origins = s.ALLOWED_ORIGINS_LIST
        assert "http://localhost:3000" in origins

def test_T10_cors_multiple_origins():
    from app.core.config import Settings
    s = Settings(ALLOWED_ORIGINS="https://a.com,https://b.com,https://c.com")
    assert len(s.ALLOWED_ORIGINS_LIST) == 3


# ── T11-T14: Alertmanager rules ───────────────────────────────────────────
def test_T11_alertmanager_rules_exist():
    assert os.path.exists("../monitoring/alertmanager_rules.yml") or \
           os.path.exists("monitoring/alertmanager_rules.yml") or \
           os.path.exists("backend/monitoring/alertmanager_rules.yml")

def test_T12_alertmanager_has_unscr_alert():
    for path in ["../monitoring/alertmanager_rules.yml",
                 "monitoring/alertmanager_rules.yml",
                 "backend/monitoring/alertmanager_rules.yml"]:
        if os.path.exists(path):
            content = open(path).read()
            assert "UNSCRFeedStale" in content
            assert "EDDCasesOverdue" in content
            return
    pytest.skip("alertmanager_rules.yml not found")

def test_T13_alertmanager_has_bfiu_refs():
    for path in ["../monitoring/alertmanager_rules.yml",
                 "monitoring/alertmanager_rules.yml",
                 "backend/monitoring/alertmanager_rules.yml"]:
        if os.path.exists(path):
            content = open(path).read()
            assert "bfiu_ref" in content
            return
    pytest.skip("alertmanager_rules.yml not found")

def test_T14_protected_prefixes_count():
    from app.middleware.admin_ip_whitelist import PROTECTED_PREFIXES
    assert len(PROTECTED_PREFIXES) >= 3


# ── T15-T16: Integration ──────────────────────────────────────────────────
def test_T15_middleware_imported():
    from app.middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware
    assert AdminIPWhitelistMiddleware is not None

def test_T16_logging_config_imported():
    from app.core.logging_config import configure_logging, JSONFormatter
    assert configure_logging is not None
    assert JSONFormatter is not None
