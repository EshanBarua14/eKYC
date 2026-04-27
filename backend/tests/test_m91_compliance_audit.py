"""M91 -- BFIU Circular No. 29 compliance audit tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_workflow_engine_importable():
    from app.services.kyc_workflow_engine import (
        create_kyc_session, SIMPLIFIED_STEPS, REGULAR_STEPS
    )
    assert create_kyc_session is not None

def test_T02_simplified_steps_complete():
    from app.services.kyc_workflow_engine import SIMPLIFIED_STEPS
    required = ["data_capture","nid_verification","biometric","screening","decision"]
    for s in required:
        assert s in SIMPLIFIED_STEPS

def test_T03_regular_steps_complete():
    from app.services.kyc_workflow_engine import REGULAR_STEPS
    required = ["data_capture","nid_verification","biometric","screening","beneficial_owner","risk_assessment","decision"]
    for s in required:
        assert s in REGULAR_STEPS

def test_T04_bo_before_risk_in_regular():
    from app.services.kyc_workflow_engine import REGULAR_STEPS
    assert REGULAR_STEPS.index("beneficial_owner") < REGULAR_STEPS.index("risk_assessment")

def test_T05_unscr_screening_importable():
    from app.services.screening_service import screen_unscr
    assert callable(screen_unscr)

def test_T06_pep_screening_importable():
    from app.services.screening_service import screen_pep
    assert callable(screen_pep)

def test_T07_risk_grading_importable():
    from app.services.risk_grading_service import calculate_risk_score
    assert callable(calculate_risk_score)

def test_T08_audit_log_model_exists():
    from app.db.models import AuditLog
    assert AuditLog is not None
