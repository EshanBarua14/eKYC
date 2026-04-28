# -*- coding: utf-8 -*-
"""
G11 - SECRET_KEY production enforcement
BFIU S4.5 - encryption keys must be properly managed.
Startup must CRASH (ValueError/ValidationError) if SECRET_KEY is default/weak in production.
"""
import pytest
import os
import sys


def make_settings(secret_key: str, debug: bool):
    """Instantiate Settings directly, bypassing .env file."""
    # Must patch env BEFORE importing — use monkeypatch via direct env manipulation
    env_patch = {
        "SECRET_KEY": secret_key,
        "DEBUG": "false" if not debug else "true",
        "DATABASE_URL": "sqlite:///./test_g11.db",
        "POSTGRES_PASSWORD": "strongpassword123",
    }
    old_env = {k: os.environ.get(k) for k in env_patch}
    os.environ.update(env_patch)

    try:
        # Remove cached module so Settings re-evaluates validators
        for mod in list(sys.modules.keys()):
            if "app.core.config" in mod or "app.core" == mod:
                del sys.modules[mod]
        from app.core.config import Settings
        s = Settings()
        return s, None
    except Exception as e:
        return None, e
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for mod in list(sys.modules.keys()):
            if "app.core.config" in mod or "app.core" == mod:
                del sys.modules[mod]


def test_default_secret_key_crashes_in_production():
    """BFIU S4.5 - default key must crash on prod startup."""
    _, err = make_settings("dev-secret-change-in-production", debug=False)
    assert err is not None, "Expected error - default SECRET_KEY must crash in prod"
    assert any(x in str(err) for x in ("SECRET_KEY", "BLOCKED", "default", "weak"))


def test_weak_short_secret_key_crashes_in_production():
    """Key under 32 chars must crash in prod."""
    _, err = make_settings("tooshort", debug=False)
    assert err is not None, "Expected error - short SECRET_KEY must crash in prod"


def test_strong_secret_key_passes_in_production():
    """Valid 64-char hex key must NOT crash."""
    import secrets
    strong = secrets.token_hex(32)
    s, err = make_settings(strong, debug=False)
    assert err is None, f"Strong key should not raise: {err}"
    assert s is not None


def test_default_secret_key_allowed_in_dev():
    """Dev mode (DEBUG=True) must NOT crash on default key - only warn."""
    _, err = make_settings("dev-secret-change-in-production", debug=True)
    assert err is None, f"Default key in dev mode must not crash: {err}"


def test_empty_secret_key_crashes_in_production():
    """Empty key must crash in prod."""
    _, err = make_settings("", debug=False)
    assert err is not None, "Empty SECRET_KEY must crash in prod"
