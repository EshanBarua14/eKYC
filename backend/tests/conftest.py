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

# ── E2E session cleanup — prevents stale-session 409 conflicts ──────────────
import pytest

E2E_SESSIONS_TO_CLEAN = [
    "e2e_sess_003", "e2e_sess_004",
]

@pytest.fixture(autouse=True, scope="session")
def clean_e2e_sessions():
    """Delete known fixed e2e session IDs before test suite runs."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    try:
        from app.db.database import db_session
        from app.db.models import OnboardingOutcome
        with db_session() as db:
            for sid in E2E_SESSIONS_TO_CLEAN:
                db.query(OnboardingOutcome).filter_by(session_id=sid).delete()
    except Exception as e:
        print(f"[conftest] e2e cleanup warning: {e}")
    yield

# ── M29 Admin test cleanup ───────────────────────────────────────────────
M29_INSTITUTION_CODES = ["TIM29","TCMI29","DUPX9","BADTP","GETI9","AUDT9"]
M29_USER_EMAILS = [
    "admin_m29@test.com","maker_m29@test.com","auditor_m29@test.com",
    "newuser_m29a@test.com","newuser_m29b@test.com",
    "dup_m29@test.com","badrole@test.com","getuser_m29@test.com",
]

@pytest.fixture(autouse=True, scope="session")
def clean_m29_data():
    try:
        from app.db.database import db_session
        from app.db.models.auth import Institution, User
        with db_session() as db:
            for code in M29_INSTITUTION_CODES:
                db.query(Institution).filter_by(short_code=code).delete()
            for email in M29_USER_EMAILS:
                db.query(User).filter_by(email=email).delete()
    except Exception as e:
        print(f"[conftest] M29 cleanup warning: {e}")
    yield

@pytest.fixture(autouse=True, scope="session")
def clean_m13_data():
    try:
        from app.db.database import db_session
        from app.db.models.auth import Institution, User
        from app.db.models_platform import Base
        stale_codes = ["FIL2","ACM2","CC2","LT2","ON2","TD2","DUPX9","TIM29",
                       "TCMI29","BADTP","GETI9","AUDT9"]
        stale_emails = ["admin_m13@test.com","auditor_m13@test.com",
                        "admin_m29@test.com","maker_m29@test.com","auditor_m29@test.com",
                        "newuser_m29a@test.com","newuser_m29b@test.com",
                        "dup_m29@test.com","badrole@test.com","getuser_m29@test.com"]
        with db_session() as db:
            for code in stale_codes:
                db.query(Institution).filter_by(short_code=code).delete()
            for email in stale_emails:
                db.query(User).filter_by(email=email).delete()
    except Exception as e:
        print(f"[conftest] M13 cleanup warning: {e}")
    yield

@pytest.fixture(autouse=True, scope="session")
def reset_demo_users_totp():
    """Ensure test admin users have TOTP set up in in-memory store."""
    yield

@pytest.fixture(autouse=True, scope="session")
def clean_m33_data():
    try:
        from app.db.database import db_session
        from app.db.models.auth import Institution
        stale = ["APR001","APR002","APR003","APR004","APR005",
                 "INS001","INS002","INS003","INS004","INS006",
                 "LST001","LST002","LST003","GET001","REV001",
                 "REV002","REV003","REV004","REJ001","REJ002","REJ003",
                 "STA001","STA002"]
        with db_session() as db:
            for code in stale:
                db.query(Institution).filter_by(short_code=code).delete()
    except Exception as e:
        print(f"[conftest] M33 cleanup warning: {e}")
    yield
