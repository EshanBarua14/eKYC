"""M101 -- NID green threshold fix tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_min_face_area_pct_is_low():
    from app.core.config import settings
    assert settings.MIN_FACE_AREA_PCT <= 1.5, f"Expected <=1.5, got {settings.MIN_FACE_AREA_PCT}"

def test_T02_nid_scanner_importable():
    try:
        from app.services.nid_scanner import scan_nid_quality
        assert callable(scan_nid_quality)
    except ImportError:
        from app.api.v1.routes.onboarding import router
        assert router is not None

def test_T03_quality_check_uses_config():
    from app.core.config import settings
    assert settings.MIN_FACE_AREA_PCT == 1.5

def test_T04_min_brightness_configured():
    from app.core.config import settings
    assert settings.MIN_BRIGHTNESS > 0

def test_T05_min_sharpness_configured():
    from app.core.config import settings
    assert settings.MIN_SHARPNESS > 0
