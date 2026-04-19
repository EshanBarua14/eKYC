"""pytest conftest — test isolation for DB-backed services"""
import pytest
from app.db.database import engine
from sqlalchemy import text

@pytest.fixture(autouse=True, scope="session")
def clean_test_outcomes():
    """Clear outcome/fallback tables before test session to avoid 409 conflicts."""
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM onboarding_outcomes WHERE session_id LIKE 'test_%' OR session_id LIKE 'sess_%' OR session_id LIKE 'sec_%'"))
            conn.execute(text("DELETE FROM fallback_cases WHERE session_id LIKE 'test_%' OR session_id LIKE 'sess_%'"))
            conn.execute(text("DELETE FROM bo_accounts WHERE session_id LIKE 'test_%' OR session_id LIKE 'sess_%'"))
            conn.execute(text("DELETE FROM kyc_profiles WHERE session_id LIKE 'test_%' OR session_id LIKE 'sess_%'"))
            conn.execute(text("DELETE FROM notification_logs WHERE session_id LIKE 'test_%' OR session_id LIKE 'sess_%'"))
            conn.commit()
    except Exception as e:
        print(f"[conftest] cleanup warning: {e}")
    yield
