"""
Xpert Fintech eKYC Platform
KYC Lifecycle Routes - M10
POST /lifecycle/register        - Register profile in lifecycle manager
GET  /lifecycle/due-reviews     - Get profiles due for review
POST /lifecycle/complete-review - Mark review complete
POST /lifecycle/declare/generate - Generate self-declaration token
POST /lifecycle/declare/{token} - Submit self-declaration
POST /lifecycle/upgrade/initiate - Initiate Simplified->Regular upgrade
POST /lifecycle/upgrade/complete - Complete upgrade
POST /lifecycle/close           - Close account (5yr retention)
GET  /lifecycle/profile/{id}    - Get lifecycle profile
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.lifecycle_service import (
    register_profile, get_profile, get_all_profiles,
    get_due_reviews, complete_review,
    generate_declaration_token, submit_declaration, get_declaration,
    initiate_upgrade, complete_upgrade,
    close_account,
    REVIEW_FREQUENCY_YEARS, DECLARATION_TOKEN_TTL_HOURS,
    ADDRESS_CHANGE_SLA_DAYS,
)

router   = APIRouter(prefix="/lifecycle", tags=["KYC Lifecycle"])
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

class RegisterRequest(BaseModel):
    profile_id:  str
    kyc_type:    str
    risk_grade:  str
    full_name:   str
    mobile:      str
    email:       Optional[str] = None
    opened_at:   Optional[str] = None

class CompleteReviewRequest(BaseModel):
    profile_id: str

class DeclareGenerateRequest(BaseModel):
    profile_id: str
    mobile:     str
    email:      Optional[str] = None

class DeclareSubmitRequest(BaseModel):
    full_name:      str
    nid_number:     str
    contact_number: str
    ip_address:     Optional[str] = None

class UpgradeInitiateRequest(BaseModel):
    profile_id:   str
    reason:       str
    requested_by: str

class UpgradeCompleteRequest(BaseModel):
    upgrade_id:      str
    additional_info: dict

class CloseRequest(BaseModel):
    profile_id: str
    reason:     str

@router.post("/register", status_code=201)
def register(req: RegisterRequest, current_user: dict = Depends(get_current_user)):
    """Register a KYC profile in the lifecycle manager."""
    valid_grades = ["HIGH", "MEDIUM", "LOW"]
    if req.risk_grade.upper() not in valid_grades:
        raise HTTPException(status_code=422, detail=f"risk_grade must be one of {valid_grades}")
    return register_profile(
        req.profile_id, req.kyc_type, req.risk_grade,
        req.full_name, req.mobile, req.email, req.opened_at,
    )

@router.get("/due-reviews")
def due_reviews(
    days_ahead: int = 30,
    current_user: dict = Depends(get_current_user),
):
    """Get profiles whose review is due within days_ahead days."""
    return {"due_reviews": get_due_reviews(days_ahead), "days_ahead": days_ahead}

@router.post("/complete-review")
def complete_review_endpoint(
    req: CompleteReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Mark a periodic review as complete and schedule next review."""
    result = complete_review(req.profile_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/declare/generate", status_code=201)
def declare_generate(
    req: DeclareGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate 48-hour self-declaration token for no-change scenario."""
    profile = get_profile(req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return generate_declaration_token(req.profile_id, req.mobile, req.email)

@router.post("/declare/{token}")
def declare_submit(token: str, req: DeclareSubmitRequest):
    """Submit self-declaration (no auth required - customer-facing link)."""
    result = submit_declaration(
        token, req.full_name, req.nid_number,
        req.contact_number, req.ip_address,
    )
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result

@router.post("/upgrade/initiate", status_code=201)
def upgrade_initiate(
    req: UpgradeInitiateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Initiate Simplified to Regular eKYC upgrade."""
    result = initiate_upgrade(req.profile_id, req.reason, req.requested_by)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result

@router.post("/upgrade/complete")
def upgrade_complete(
    req: UpgradeCompleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Complete upgrade after additional info collected."""
    result = complete_upgrade(req.upgrade_id, req.additional_info)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result

@router.post("/close")
def close(req: CloseRequest, current_user: dict = Depends(get_current_user)):
    """Close account and start 5-year retention countdown."""
    result = close_account(req.profile_id, req.reason)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/profile/{profile_id}")
def get_profile_endpoint(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get lifecycle profile by ID."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.get("/policy")
def get_policy(current_user: dict = Depends(get_current_user)):
    """Return BFIU lifecycle policy parameters."""
    return {
        "review_frequency_years":     REVIEW_FREQUENCY_YEARS,
        "declaration_token_ttl_hours": DECLARATION_TOKEN_TTL_HOURS,
        "address_change_sla_days":    ADDRESS_CHANGE_SLA_DAYS,
        "data_retention_years":       5,
        "bfiu_ref":                   "BFIU Circular No. 29 - Section 5.7",
    }
