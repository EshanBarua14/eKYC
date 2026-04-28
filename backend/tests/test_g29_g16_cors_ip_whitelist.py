# -*- coding: utf-8 -*-
"""
G29 - CORS locked to production origins (BFIU s4.5)
G16 - Admin endpoint IP whitelist (BFIU s4.5)
"""
import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────

def reload_settings(env_patch: dict):
    old = {k: os.environ.get(k) for k in env_patch}
    os.environ.update(env_patch)
    # purge ALL app modules to force full reload
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]
    try:
        from app.core.config import Settings
        s = Settings()
        # evaluate computed_field while env still patched; cache on instance
        s._cached_origins = s.ALLOWED_ORIGINS_LIST
        return s, None
    except Exception as e:
        return None, e
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for mod in list(sys.modules.keys()):
            if mod.startswith("app."):
                del sys.modules[mod]


# ── G29: CORS tests ───────────────────────────────────────────────────────

def test_cors_localhost_stripped_in_production():
    """In prod, localhost origins must be stripped from ALLOWED_ORIGINS_LIST."""
    import secrets
    s, err = reload_settings({
        "DEBUG": "false",
        "SECRET_KEY": secrets.token_hex(32),
        "ALLOWED_ORIGINS": "http://localhost:5173,https://ekyc.xpertfintech.com",
        "DATABASE_URL": "sqlite:///./test.db",
        "POSTGRES_PASSWORD": "strongpass123",
    })
    assert err is None, f"Unexpected error: {err}"
    origins = s._cached_origins
    assert "http://localhost:5173" not in origins
    assert "https://ekyc.xpertfintech.com" in origins


def test_cors_only_localhost_crashes_in_production():
    """In prod, if ALL origins are localhost → must crash (ValueError)."""
    import secrets
    s, err = reload_settings({
        "DEBUG": "false",
        "SECRET_KEY": secrets.token_hex(32),
        "ALLOWED_ORIGINS": "http://localhost:5173,http://127.0.0.1:3000",
        "DATABASE_URL": "sqlite:///./test.db",
        "POSTGRES_PASSWORD": "strongpass123",
    })
    assert err is not None, "Expected ValueError — only localhost origins in prod"
    assert "G29" in str(err) or "PRODUCTION" in str(err) or "ALLOWED_ORIGINS" in str(err)


def test_cors_production_origins_pass():
    """Valid production origin must pass without error."""
    import secrets
    s, err = reload_settings({
        "DEBUG": "false",
        "SECRET_KEY": secrets.token_hex(32),
        "ALLOWED_ORIGINS": "https://ekyc.xpertfintech.com,https://app.xpertfintech.com",
        "DATABASE_URL": "sqlite:///./test.db",
        "POSTGRES_PASSWORD": "strongpass123",
    })
    assert err is None, f"Unexpected error: {err}"
    assert "https://ekyc.xpertfintech.com" in s.ALLOWED_ORIGINS_LIST


def test_cors_localhost_allowed_in_dev():
    """Dev mode must allow localhost origins."""
    s, err = reload_settings({
        "DEBUG": "true",
        "ALLOWED_ORIGINS": "http://localhost:5173,http://localhost:3000",
        "DATABASE_URL": "sqlite:///./test.db",
    })
    assert err is None, f"Dev mode must not crash: {err}"
    assert "http://localhost:5173" in s.ALLOWED_ORIGINS_LIST


# ── G16: Admin IP whitelist middleware tests ──────────────────────────────

@pytest.fixture
def whitelist_middleware():
    for mod in list(sys.modules.keys()):
        if "admin_ip_whitelist" in mod:
            del sys.modules[mod]
    from app.middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware
    return AdminIPWhitelistMiddleware


def make_request(path: str, client_ip: str, forwarded: str = None):
    req = MagicMock()
    req.url.path = path
    req.client.host = client_ip
    req.headers = {}
    if forwarded:
        req.headers = {"X-Forwarded-For": forwarded}
    return req


@pytest.mark.asyncio
async def test_admin_ip_blocked_when_whitelist_set(whitelist_middleware):
    """Request from non-whitelisted IP to /api/v1/admin must return 403."""
    os.environ["ADMIN_IP_WHITELIST"] = "10.0.0.1,10.0.0.2"
    try:
        app_mock = MagicMock()
        mw = whitelist_middleware(app_mock)
        req = make_request("/api/v1/admin/users", "1.2.3.4")
        call_next = AsyncMock()
        resp = await mw.dispatch(req, call_next)
        assert resp.status_code == 403
        call_next.assert_not_called()
    finally:
        os.environ.pop("ADMIN_IP_WHITELIST", None)


@pytest.mark.asyncio
async def test_admin_ip_allowed_when_whitelisted(whitelist_middleware):
    """Request from whitelisted IP must pass through."""
    os.environ["ADMIN_IP_WHITELIST"] = "10.0.0.1,10.0.0.2"
    try:
        app_mock = MagicMock()
        mw = whitelist_middleware(app_mock)
        req = make_request("/api/v1/admin/users", "10.0.0.1")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        resp = await mw.dispatch(req, call_next)
        call_next.assert_called_once()
    finally:
        os.environ.pop("ADMIN_IP_WHITELIST", None)


@pytest.mark.asyncio
async def test_admin_empty_whitelist_allows_all(whitelist_middleware):
    """Empty whitelist = dev mode = allow all IPs."""
    os.environ["ADMIN_IP_WHITELIST"] = ""
    try:
        app_mock = MagicMock()
        mw = whitelist_middleware(app_mock)
        req = make_request("/api/v1/admin/users", "1.2.3.4")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        await mw.dispatch(req, call_next)
        call_next.assert_called_once()
    finally:
        os.environ.pop("ADMIN_IP_WHITELIST", None)


@pytest.mark.asyncio
async def test_non_admin_path_not_blocked(whitelist_middleware):
    """Non-admin paths must never be blocked by IP whitelist."""
    os.environ["ADMIN_IP_WHITELIST"] = "10.0.0.1"
    try:
        app_mock = MagicMock()
        mw = whitelist_middleware(app_mock)
        req = make_request("/api/v1/kyc/session", "1.2.3.4")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        await mw.dispatch(req, call_next)
        call_next.assert_called_once()
    finally:
        os.environ.pop("ADMIN_IP_WHITELIST", None)


@pytest.mark.asyncio
async def test_forwarded_for_header_used(whitelist_middleware):
    """X-Forwarded-For header IP must be used (proxy-aware)."""
    os.environ["ADMIN_IP_WHITELIST"] = "10.0.0.5"
    try:
        app_mock = MagicMock()
        mw = whitelist_middleware(app_mock)
        req = make_request("/api/v1/admin/users", "proxy_ip", forwarded="10.0.0.5")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        await mw.dispatch(req, call_next)
        call_next.assert_called_once()
    finally:
        os.environ.pop("ADMIN_IP_WHITELIST", None)
