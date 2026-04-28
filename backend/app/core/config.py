"""
Xpert Fintech eKYC Platform
Core configuration â M43 Secrets Management
All secrets from environment variables with validation.
Startup check fails fast if required secrets are missing in production.
"""
import os
import sys
import logging
from typing import List, Optional
from pydantic import field_validator, model_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ââ App âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    APP_NAME: str    = "Xpert Fintech Ltd. - Electronic KYC (eKYC) Compliance API"
    TIMEZONE: str    = "Asia/Dhaka"   # Bangladesh Standard Time UTC+6
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool      = True
    SECRET_KEY: str  = "dev-secret-change-in-production"
    SQL_ECHO: bool   = False

    # ââ Database ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    DATABASE_URL: str      = "sqlite:///./ekyc.db"
    POSTGRES_HOST: str     = "localhost"
    POSTGRES_PORT: int     = 5432
    POSTGRES_DB: str       = "ekyc_db"
    POSTGRES_USER: str     = "ekyc_user"
    POSTGRES_PASSWORD: str = "ekyc_pass"

    # ââ SQLite fallback âââââââââââââââââââââââââââââââââââââââââââââââââââ
    SQLITE_URL: str = "sqlite:///./ekyc.db"

    # ââ Redis âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str  = "redis://localhost:6379/0"

    # ââ Celery ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    CELERY_BROKER_URL: str     = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ââ CORS ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    @computed_field
    @property
    def ALLOWED_ORIGINS_LIST(self) -> List[str]:
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]
        import os
        is_prod = os.getenv("DEBUG", "true").lower() == "false"
        if is_prod:
            unsafe = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
            if unsafe:
                import logging
                logging.getLogger(__name__).warning(
                    "[M66] CORS allows localhost in production: %s â set ALLOWED_ORIGINS to production domain.",
                    unsafe
                )
        return origins

    # ââ Multi-tenant ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    DEFAULT_TENANT_SCHEMA: str = "public"

    # ââ Liveness thresholds (BFIU Annexure-2) ââââââââââââââââââââââââââââ
    MIN_BRIGHTNESS: float    = 20.0
    MAX_BRIGHTNESS: float    = 254.0
    MIN_SHARPNESS: float     = 30.0
    MIN_WIDTH: int           = 160
    MIN_HEIGHT: int          = 120
    MIN_FACE_AREA_PCT: float = 1.5

    # ââ Face matching âââââââââââââââââââââââââââââââââââââââââââââââââââââ
    MATCH_THRESHOLD: float  = 35.0
    REVIEW_THRESHOLD: float = 25.0

    # ââ BFIU ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    BFIU_GUIDELINE: str                = "BFIU Circular No. 29"
    BFIU_SECTION: str                  = "3.3 - Customer Onboarding by Face-Matching"
    BFIU_ANNEXURE: str                 = "Annexure-2 - Instructions for Photo Capture"
    BFIU_MAX_ATTEMPTS_PER_SESSION: int = 999
    BFIU_MAX_SESSIONS_PER_DAY: int     = 999

    # ââ JWT (M43 â move from security.py hardcodes) âââââââââââââââââââââââ
    JWT_ALGORITHM: str          = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ââ Validators ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_not_be_default_in_prod(cls, v: str) -> str:
        import os
        is_prod = os.getenv("DEBUG", "true").lower() == "false"
        defaults = {"dev-secret-change-in-production", "CHANGE_ME_REQUIRED_min_64_chars_hex", ""}
        if v in defaults or len(v) < 32:
            if is_prod:
                raise ValueError(
                    "[M64] SECRET_KEY is default/weak in production. "
                    "Generate with: python -c 'import secrets; print(secrets.token_hex(32))' "
                    "BFIU Â§4.5 â encryption keys must be properly managed."
                )
            else:
                log.warning("[M43] SECRET_KEY is using the default dev value. Set SECRET_KEY env var in production.")
        return v

    @field_validator("POSTGRES_PASSWORD")
    @classmethod
    def postgres_password_must_not_be_default_in_prod(cls, v: str) -> str:
        if v in ("ekyc_pass", "postgres", "password", ""):
            log.warning(
                "[M43] POSTGRES_PASSWORD is using a weak/default value. "
                "Set a strong password in production."
            )
        return v

    @model_validator(mode="after")
    def production_secrets_check(self) -> "Settings":
        """Warn loudly (but don't crash) if weak secrets detected."""
        if not self.DEBUG:
            issues = []
            if self.SECRET_KEY == "dev-secret-change-in-production":
                issues.append("SECRET_KEY is default")
            if self.POSTGRES_PASSWORD in ("ekyc_pass", "postgres", "password"):
                issues.append("POSTGRES_PASSWORD is weak")
            if issues:
                msg = (
                    "[G11] PRODUCTION STARTUP BLOCKED: " + ", ".join(issues) +
                    "  -  BFIU §4.5 requires strong secrets in production. "
                    "Generate SECRET_KEY: python -c 'import secrets; print(secrets.token_hex(32))'"
                )
                log.critical(msg)
                raise ValueError(msg)
        return self

    # ââ Computed DB URL (overrides DATABASE_URL if postgres vars set) âââââ
    @computed_field
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


def check_secrets() -> list[str]:
    """
    Startup secrets check â call from main.py on_event('startup').
    Returns list of warnings (empty = all good).
    """
    warnings = []
    s = settings

    if s.SECRET_KEY == "dev-secret-change-in-production":
        warnings.append("SECRET_KEY: using default dev value")
    if len(s.SECRET_KEY) < 32:
        warnings.append("SECRET_KEY: too short (minimum 32 chars)")
    if s.POSTGRES_PASSWORD in ("ekyc_pass", "postgres", "password", ""):
        warnings.append("POSTGRES_PASSWORD: weak or default value")
    if s.DEBUG and not s.DATABASE_URL.startswith("sqlite"):
        pass   # DEBUG=True with PostgreSQL is fine for dev
    if "localhost" not in s.REDIS_URL and "127.0.0.1" not in s.REDIS_URL:
        pass   # Remote Redis â fine

    return warnings


settings = Settings()
