"""
M58 — KYC Workflow Routes
BFIU Circular No. 29 — Full compliant workflow engine

POST /kyc-workflow/session               - Start KYC session
POST /kyc-workflow/{id}/data-capture     - Step 1: customer data
POST /kyc-workflow/{id}/nid-verify       - Step 2: NID verification
POST /kyc-workflow/{id}/biometric        - Step 3: biometric result
POST /kyc-workflow/{id}/screening        - Step 4: UNSCR/PEP screening
POST /kyc-workflow/{id}/beneficial-owner - Step 5: BO identification (Regular only) §4.2
POST /kyc-workflow/{id}/risk             - Step 6: risk assessment (Regular only)
POST /kyc-workflow/{id}/decision         - Final: decision
GET  /kyc-workflow/{id}                  - Get session state
GET  /kyc-workflow/{id}/summary          - Full summary for audit
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import JWTError
from app.core.security import decode_token
from app.services.kyc_workflow_engine import (
    create_kyc_session, get_kyc_session, get_session_summary,
    submit_data_capture, submit_nid_verification, submit_biometric,
    submit_screening, submit_beneficial_owner, submit_risk_assessment, make_decision,
)

router   = APIRouter(prefix="/kyc-workflow", tags=["KYC Workflow"])
security = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return decode_token(creds.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _get_session_or_404(session_id: str) -> dict:
    s = get_kyc_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": f"Session {session_id} not found"})
    return s


# ── Schemas ───────────────────────────────────────────────────────────────
class StartSessionReq(BaseModel):
    kyc_type:       str = "SIMPLIFIED"
    agent_id:       str = "system"
    channel:        str = "AGENCY"
    institution_id: str = "default"

class DataCaptureReq(BaseModel):
    full_name_en:    str
    date_of_birth:   str
    mobile_phone:    str
    present_address: str
    permanent_address: Optional[str] = None
    fathers_name:    Optional[str] = None
    mothers_name:    Optional[str] = None
    spouse_name:     Optional[str] = None
    gender:          Optional[str] = None
    profession:      Optional[str] = None
    monthly_income:  Optional[int] = None
    source_of_funds: Optional[str] = None
    nationality:     Optional[str] = "Bangladeshi"
    tin:             Optional[str] = None

class NIDVerifyReq(BaseModel):
    nid_number:  str
    ocr_fields:  Optional[dict] = None

class BiometricReq(BaseModel):
    passed:              bool
    confidence:          float
    method:              str = "FACE_MATCH"
    liveness_passed:     Optional[bool] = None
    failed_session_count: Optional[int] = 1

class ScreeningReq(BaseModel):
    name: Optional[str] = None

class RiskReq(BaseModel):
    onboarding_channel: str = "AGENCY"
    residency:          str = "RESIDENT"
    pep_ip_status:      str = "NONE"
    product_type:       str = "ORDINARY_LIFE"
    institution_type:   str = "INSURANCE"
    business_type:      str = "OTHER"
    profession:         Optional[str] = None
    monthly_income:     Optional[int] = None
    source_of_funds:    Optional[str] = None


class BeneficialOwnerReq(BaseModel):
    """G01 Fix: §4.2 Beneficial ownership — mandatory step for Regular eKYC."""
    has_beneficial_owner: bool
    bo_name:              Optional[str] = None
    bo_nid:               Optional[str] = None
    bo_ownership_pct:     Optional[float] = None
    bo_is_pep:            Optional[bool] = None
    bo_cdd_done:          Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────
@router.post("/session", status_code=201)
def start_session(req: StartSessionReq, _=Depends(get_current_user)):
    """Start a new BFIU-compliant KYC workflow session."""
    kyc_type = req.kyc_type.upper()
    if kyc_type not in ("SIMPLIFIED", "REGULAR"):
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_KYC_TYPE", "message": "kyc_type must be SIMPLIFIED or REGULAR"})
    return create_kyc_session(
        kyc_type=kyc_type,
        agent_id=req.agent_id,
        channel=req.channel,
        institution_id=req.institution_id,
    )


@router.get("/{session_id}")
def get_session(session_id: str, _=Depends(get_current_user)):
    return _get_session_or_404(session_id)


@router.get("/{session_id}/summary")
def session_summary(session_id: str, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    return get_session_summary(session_id)


@router.post("/{session_id}/data-capture")
def data_capture(session_id: str, req: DataCaptureReq, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    try:
        result = submit_data_capture(session_id, req.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result)
    return result


@router.post("/{session_id}/nid-verify")
def nid_verify(session_id: str, req: NIDVerifyReq, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    try:
        result = submit_nid_verification(session_id, req.nid_number, req.ocr_fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result)
    return result


@router.post("/{session_id}/biometric")
def biometric(session_id: str, req: BiometricReq, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    try:
        result = submit_biometric(session_id, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/{session_id}/screening")
def screening(session_id: str, req: ScreeningReq, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    try:
        result = submit_screening(session_id, req.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/{session_id}/beneficial-owner")
def beneficial_owner(session_id: str, req: BeneficialOwnerReq, _=Depends(get_current_user)):
    """
    G01 Fix: Step 5 (Regular KYC only) — Beneficial ownership identification.
    BFIU §4.2: Mandatory for Regular eKYC. BO is PEP → EDD auto-triggered.
    """
    _get_session_or_404(session_id)
    try:
        result = submit_beneficial_owner(session_id, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result)
    return result


@router.post("/{session_id}/risk")
def risk_assessment(session_id: str, req: RiskReq, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    try:
        result = submit_risk_assessment(session_id, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result)
    return result


@router.post("/{session_id}/decision")
def decision(session_id: str, _=Depends(get_current_user)):
    _get_session_or_404(session_id)
    try:
        result = make_decision(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result
