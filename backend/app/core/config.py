"""
Xpert Fintech eKYC Platform
Core configuration — all settings in one place
"""
from typing import List

class Settings:
    # App
    APP_NAME: str        = "Xpert Fintech Ltd. — Electronic KYC (eKYC) Compliance API"
    APP_VERSION: str     = "1.0.0"
    API_V1_PREFIX: str   = "/api/v1"
    DEBUG: bool          = True

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Liveness thresholds (BFIU Annexure-2)
    MIN_BRIGHTNESS: float    = 40.0
    MAX_BRIGHTNESS: float    = 250.0
    MIN_SHARPNESS: float     = 80.0
    MIN_WIDTH: int           = 320
    MIN_HEIGHT: int          = 240
    MIN_FACE_AREA_PCT: float = 4.0

    # Face matching thresholds
    MATCH_THRESHOLD: float   = 45.0   # above → MATCHED
    REVIEW_THRESHOLD: float  = 30.0   # above → REVIEW, below → FAILED

    # BFIU reference
    BFIU_GUIDELINE: str = "BFIU Circular No. 29"
    BFIU_SECTION: str   = "3.3 — Customer Onboarding by Face-Matching"
    BFIU_ANNEXURE: str  = "Annexure-2 — Instructions for Photo Capture"

settings = Settings()
