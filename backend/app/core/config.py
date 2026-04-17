"""
Xpert Fintech eKYC Platform
Core configuration - environment-aware, multi-tenant ready
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # App
    APP_NAME: str        = os.getenv("APP_NAME", "Xpert Fintech Ltd. - Electronic KYC (eKYC) Compliance API")
    APP_VERSION: str     = os.getenv("APP_VERSION", "1.0.0")
    API_V1_PREFIX: str   = "/api/v1"
    DEBUG: bool          = os.getenv("DEBUG", "True") == "True"
    SECRET_KEY: str      = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

    # Database
    POSTGRES_HOST: str     = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int     = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str       = os.getenv("POSTGRES_DB", "ekyc_db")
    POSTGRES_USER: str     = os.getenv("POSTGRES_USER", "ekyc_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "ekyc_pass")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # SQLite fallback for local dev (existing modules)
    SQLITE_URL: str      = "sqlite:///./ekyc.db"

    # Redis
    REDIS_HOST: str      = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int      = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str       = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Multi-tenant
    DEFAULT_TENANT_SCHEMA: str = os.getenv("DEFAULT_TENANT_SCHEMA", "public")

    # Liveness thresholds (BFIU Annexure-2)
    MIN_BRIGHTNESS: float    = 40.0
    MAX_BRIGHTNESS: float    = 250.0
    MIN_SHARPNESS: float     = 80.0
    MIN_WIDTH: int           = 320
    MIN_HEIGHT: int          = 240
    MIN_FACE_AREA_PCT: float = 4.0

    # Face matching thresholds
    MATCH_THRESHOLD: float   = 45.0
    REVIEW_THRESHOLD: float  = 30.0

    # BFIU
    BFIU_GUIDELINE: str                = os.getenv("BFIU_GUIDELINE", "BFIU Circular No. 29")
    BFIU_SECTION: str                  = "3.3 - Customer Onboarding by Face-Matching"
    BFIU_ANNEXURE: str                 = "Annexure-2 - Instructions for Photo Capture"
    BFIU_MAX_ATTEMPTS_PER_SESSION: int = int(os.getenv("BFIU_MAX_ATTEMPTS_PER_SESSION", "10"))
    BFIU_MAX_SESSIONS_PER_DAY: int     = int(os.getenv("BFIU_MAX_SESSIONS_PER_DAY", "2"))

settings = Settings()
