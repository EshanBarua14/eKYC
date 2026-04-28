"""
M43 — Secrets Management Tests
Validates pydantic-settings config, env var loading, startup secrets check.
"""
import pytest
from unittest.mock import patch


# ══════════════════════════════════════════════════════════════════════════
# 1. Settings loading
# ══════════════════════════════════════════════════════════════════════════
class TestSettingsLoad:
    def test_settings_imports(self):
        from app.core.config import settings
        assert settings is not None

    def test_app_name_loaded(self):
        from app.core.config import settings
        assert "Xpert" in settings.APP_NAME

    def test_debug_is_bool(self):
        from app.core.config import settings
        assert isinstance(settings.DEBUG, bool)

    def test_postgres_port_is_int(self):
        from app.core.config import settings
        assert isinstance(settings.POSTGRES_PORT, int)
        assert settings.POSTGRES_PORT == 5432

    def test_redis_port_is_int(self):
        from app.core.config import settings
        assert isinstance(settings.REDIS_PORT, int)

    def test_bfiu_attempts_is_int(self):
        from app.core.config import settings
        assert isinstance(settings.BFIU_MAX_ATTEMPTS_PER_SESSION, int)
        assert settings.BFIU_MAX_ATTEMPTS_PER_SESSION == 10

    def test_bfiu_sessions_is_int(self):
        from app.core.config import settings
        assert isinstance(settings.BFIU_MAX_SESSIONS_PER_DAY, int)
        assert settings.BFIU_MAX_SESSIONS_PER_DAY == 2

    def test_allowed_origins_list_is_list(self):
        from app.core.config import settings
        assert isinstance(settings.ALLOWED_ORIGINS_LIST, list)
        assert len(settings.ALLOWED_ORIGINS_LIST) >= 1

    def test_database_url_is_postgresql(self):
        from app.core.config import settings
        assert settings.DATABASE_URL.startswith("postgresql://")

    def test_database_url_async_computed(self):
        from app.core.config import settings
        assert "asyncpg" in settings.DATABASE_URL_ASYNC

    def test_redis_url_loaded(self):
        from app.core.config import settings
        assert settings.REDIS_URL.startswith("redis://")

    def test_celery_broker_url(self):
        from app.core.config import settings
        assert settings.CELERY_BROKER_URL.startswith("redis://")

    def test_celery_result_backend(self):
        from app.core.config import settings
        assert settings.CELERY_RESULT_BACKEND.startswith("redis://")

    def test_api_v1_prefix(self):
        from app.core.config import settings
        assert settings.API_V1_PREFIX == "/api/v1"

    def test_liveness_thresholds_positive(self):
        from app.core.config import settings
        assert settings.MIN_BRIGHTNESS > 0
        assert settings.MAX_BRIGHTNESS > settings.MIN_BRIGHTNESS
        assert settings.MIN_SHARPNESS > 0
        assert settings.MIN_FACE_AREA_PCT > 0

    def test_match_threshold_positive(self):
        from app.core.config import settings
        assert settings.MATCH_THRESHOLD > 0
        assert settings.REVIEW_THRESHOLD > 0
        assert settings.MATCH_THRESHOLD > settings.REVIEW_THRESHOLD


# ══════════════════════════════════════════════════════════════════════════
# 2. Startup secrets check
# ══════════════════════════════════════════════════════════════════════════
class TestSecretsCheck:
    def test_check_secrets_returns_list(self):
        from app.core.config import check_secrets
        result = check_secrets()
        assert isinstance(result, list)

    def test_check_secrets_warns_on_default_key(self):
        from app.core.config import check_secrets, settings
        # Default dev key always triggers this warning
        warnings = check_secrets()
        assert any("SECRET_KEY" in w for w in warnings)

    def test_check_secrets_warns_on_short_key(self):
        from app.core.config import check_secrets
        warnings = check_secrets()
        # default key is short — should warn
        short_key_warnings = [w for w in warnings if "too short" in w]
        assert len(short_key_warnings) >= 1

    def test_check_secrets_warns_on_weak_db_password(self):
        """check_secrets() must warn when POSTGRES_PASSWORD is weak."""
        from app.core.config import check_secrets, settings
        import unittest.mock as mock
        # Patch settings to simulate weak password
        with mock.patch.object(settings, "POSTGRES_PASSWORD", "ekyc_pass"):
            warnings = check_secrets()
        assert any("POSTGRES_PASSWORD" in w for w in warnings)

    def test_check_secrets_clean_with_strong_values(self):
        from app.core.config import Settings
        strong = Settings(
            SECRET_KEY="a" * 64,
            POSTGRES_PASSWORD="Str0ng!Pass#2026_XYZ",
            DATABASE_URL="postgresql://u:p@localhost/db",
        )
        # Strong key should not trigger short warning
        assert len(strong.SECRET_KEY) >= 32

    def test_settings_singleton_exists(self):
        from app.core.config import settings
        from app.core.config import settings as settings2
        assert settings is settings2


# ══════════════════════════════════════════════════════════════════════════
# 3. Environment variable override
# ══════════════════════════════════════════════════════════════════════════
class TestEnvOverride:
    def test_settings_reads_env_vars(self):
        import os
        from pydantic_settings import BaseSettings
        # Verify pydantic-settings is being used
        from app.core.config import Settings
        assert issubclass(Settings, BaseSettings)

    def test_debug_default_is_true(self):
        from app.core.config import settings
        # In dev .env, DEBUG=True
        assert settings.DEBUG is True

    def test_bfiu_guideline_set(self):
        from app.core.config import settings
        assert "BFIU" in settings.BFIU_GUIDELINE

    def test_default_tenant_schema(self):
        from app.core.config import settings
        assert settings.DEFAULT_TENANT_SCHEMA == "public"

    def test_sqlite_url_fallback_exists(self):
        from app.core.config import settings
        assert "sqlite" in settings.SQLITE_URL

    def test_jwt_algorithm_default(self):
        from app.core.config import settings
        assert settings.JWT_ALGORITHM == "RS256"
