"""
Xpert Fintech eKYC Platform
Onboarding Wizard Routes - M4
BFIU Circular No. 29 - Section 3.2

POST /onboarding/start          - Start new wizard session
POST /onboarding/step           - Submit current step data
POST /onboarding/fail           - Record failed biometric session
GET  /onboarding/session/{id}   - Get session state
GET  /onboarding/steps          - List all wizard steps
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.onboarding_wizard import (
    create_wizard_session, get_wizard_session,
    process_step, record_failed_session,
    generate_notification, get_audit_trail, STEPS, STEPS_REGULAR, FALLBACK_SESSION_THRESHOLD,
    SIGNATURE_TYPES_LOW_RISK, SIGNATURE_TYPES_HIGH_RISK,
)

router   = APIRouter(prefix="/onboarding", tags=["Onboarding Wizard"])
security = HTTPBearer()

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class StartSessionRequest(BaseModel):
    nid_number:     str
    agent_id:       str
    channel:        str = "AGENCY"
    biometric_mode: str = "FINGERPRINT"
    kyc_type:       str = "SIMPLIFIED"

class StepRequest(BaseModel):
    session_id: str
    step_data:  dict

class FailSessionRequest(BaseModel):
    session_id: str
    reason:     Optional[str] = None

# ---------------------------------------------------------------------------
# POST /onboarding/start
# ---------------------------------------------------------------------------
@router.post("/start", status_code=201)
def start_session(
    req: StartSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start a new 5-step onboarding wizard session."""
    from app.services.nid_ocr_service import validate_nid_number
    nid_check = validate_nid_number(req.nid_number)
    if not nid_check["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_NID", "message": "Invalid NID number format"}
        )

    session = create_wizard_session(
        nid_number     = req.nid_number,
        agent_id       = req.agent_id,
        channel        = req.channel,
        biometric_mode = req.biometric_mode,
        kyc_type       = req.kyc_type,
    )
    return {
        "success":           True,
        "session_id":        session["session_id"],
        "kyc_type":          session["kyc_type"],
        "current_step":      session["current_step"],
        "current_step_name": session["current_step_name"],
        "status":            session["status"],
        "total_steps":       len(session["steps_map"]),
        "bfiu_ref":          "BFIU Circular No. 29 - Section 3.2 / 3.3",
    }

# ---------------------------------------------------------------------------
# POST /onboarding/step
# ---------------------------------------------------------------------------
@router.post("/step")
def submit_step(
    req: StepRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit data for the current wizard step and advance to next."""
    session = get_wizard_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail={
            "error_code": "SESSION_NOT_FOUND",
            "message":    f"Session {req.session_id} not found",
        })

    result = process_step(req.session_id, req.step_data)

    if not result["success"]:
        raise HTTPException(status_code=422, detail={
            "error_code": "STEP_VALIDATION_FAILED",
            "message":    result["error"],
            "step":       result.get("step"),
        })

    # Auto-generate notification on step 5 completion
    notification = None
    if result["status"] == "COMPLETED":
        updated_session = get_wizard_session(req.session_id)
        notification    = generate_notification(updated_session)

    return {
        **result,
        "notification": notification,
    }

# ---------------------------------------------------------------------------
# POST /onboarding/fail
# ---------------------------------------------------------------------------
@router.post("/fail")
def fail_session(
    req: FailSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Record a failed biometric attempt for a session.
    After 3 failures, triggers face matching fallback per BFIU Section 3.2.
    """
    session = get_wizard_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail={
            "error_code": "SESSION_NOT_FOUND",
            "message":    f"Session {req.session_id} not found",
        })

    result = record_failed_session(req.session_id)
    return result

# ---------------------------------------------------------------------------
# GET /onboarding/session/{session_id}
# ---------------------------------------------------------------------------
@router.get("/session/{session_id}")
def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get current wizard session state."""
    session = get_wizard_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail={
            "error_code": "SESSION_NOT_FOUND",
            "message":    f"Session {session_id} not found",
        })
    # Never expose raw NID number in response
    safe_session = {k: v for k, v in session.items() if k != "nid_number"}
    return safe_session

# ---------------------------------------------------------------------------
# GET /onboarding/steps
# ---------------------------------------------------------------------------
@router.get("/steps")
def list_steps(current_user: dict = Depends(get_current_user), kyc_type: str = "SIMPLIFIED"):
    """List all wizard steps. kyc_type=SIMPLIFIED|REGULAR"""
    steps_map = STEPS_REGULAR if kyc_type.upper() == "REGULAR" else STEPS
    step_meta = {
        "NID_VERIFICATION":  {"description": "Enter NID number and DOB — matched against EC database", "required_fields": ["nid_number", "dob", "verified"]},
        "BIOMETRIC":         {"description": "Face match or fingerprint biometric verification (Annexure-2)", "required_fields": ["biometric_passed", "biometric_mode"]},
        "PERSONAL_INFO":     {"description": "OCR-populated personal info form with nominee fields", "required_fields": ["full_name", "mobile"]},
        "PHOTOGRAPH":        {"description": "Capture or upload customer photograph", "required_fields": ["photo_b64"]},
        "SCREENING":         {"description": "UNSCR sanctions screening (simplified) + PEP/adverse media (regular)", "required_fields": ["unscr_hit", "screening_completed"]},
        "BENEFICIAL_OWNER":  {"description": "Beneficial owner identification and CDD (regular KYC sec 4.2c)", "required_fields": ["has_beneficial_owner"]},
        "SIGNATURE":         {"description": "Wet/electronic/digital signature or PIN for low-risk", "required_fields": ["signature_type"], "allowed_types_low_risk": SIGNATURE_TYPES_LOW_RISK, "allowed_types_high_risk": SIGNATURE_TYPES_HIGH_RISK},
        "NOTIFICATION":      {"description": "Account opening notification via registered SIM and email", "required_fields": ["mobile"]},
    }
    return {
        "kyc_type":   kyc_type.upper(),
        "total_steps": len(steps_map),
        "steps": [
            {"step_number": n, "name": name, **step_meta.get(name, {})}
            for n, name in steps_map.items()
        ],
        "fallback_threshold": FALLBACK_SESSION_THRESHOLD,
        "fallback_action":    "Face matching offered after 3 failed sessions",
        "bfiu_ref":           "BFIU Circular No. 29 - Section 3.2 / 3.3",
    }


@router.get("/session/{session_id}/audit")
def get_session_audit(session_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve audit trail for a session (BFIU sec 3.2.3 / 3.3.3)."""
    return get_audit_trail(session_id)
