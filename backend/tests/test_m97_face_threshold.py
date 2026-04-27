"""M97 -- Face match threshold fix tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_match_threshold_configured():
    from app.core.config import settings
    assert hasattr(settings, "MATCH_THRESHOLD")
    assert settings.MATCH_THRESHOLD > 0

def test_T02_review_threshold_configured():
    from app.core.config import settings
    assert hasattr(settings, "REVIEW_THRESHOLD")
    assert settings.REVIEW_THRESHOLD > 0

def test_T03_match_above_review():
    from app.core.config import settings
    assert settings.MATCH_THRESHOLD > settings.REVIEW_THRESHOLD

def test_T04_face_verifier_importable():
    from app.services.face_match import compare_faces
    assert callable(compare_faces)

def test_T05_nid_face_area_threshold():
    from app.core.config import settings
    assert hasattr(settings, "MIN_FACE_AREA_PCT")
    assert settings.MIN_FACE_AREA_PCT <= 2.0, "Threshold too high for faded NIDs"
