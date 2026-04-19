"""
Xpert Fintech eKYC Platform
Screening Routes - M9
POST /screening/unscr          - UNSCR sanctions check
POST /screening/pep            - PEP/IP screening (Regular eKYC only)
POST /screening/adverse-media  - Adverse media check
POST /screening/exit-list/add  - Add to institution exit list
POST /screening/exit-list/check - Check against exit list
POST /screening/full           - Run all applicable checks
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.screening_service import (
    screen_unscr, screen_pep, screen_adverse_media,
    screen_exit_list, add_to_exit_list, run_full_screening,
    UNSCR_FUZZY_MATCH_THRESHOLD, PEP_MATCH_THRESHOLD,
)

router   = APIRouter(prefix="/screening", tags=["Sanctions and Screening"])
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

class ScreenRequest(BaseModel):
    name:           str
    kyc_type:       str = "SIMPLIFIED"
    institution_id: str = "DEMO"

class ExitListAddRequest(BaseModel):
    institution_id: str
    name:           str
    reason:         str

class ExitListCheckRequest(BaseModel):
    name:           str
    institution_id: str

@router.post("/unscr")
async def unscr_check(req: ScreenRequest, current_user: dict = Depends(get_current_user)):
    """Screen name against UNSCR consolidated list. Mandatory for all eKYC types."""
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    return screen_unscr(req.name)

@router.post("/pep")
async def pep_check(req: ScreenRequest, current_user: dict = Depends(get_current_user)):
    """Screen name against PEP/IP list. Mandatory for Regular eKYC only."""
    if req.kyc_type.upper() == "SIMPLIFIED":
        return {
            "verdict":    "SKIPPED",
            "reason":     "PEP screening not required for SIMPLIFIED eKYC",
            "kyc_type":   req.kyc_type,
            "bfiu_ref":   "BFIU Circular No. 29 - Section 4.2",
        }
    return screen_pep(req.name)

@router.post("/adverse-media")
async def adverse_media_check(req: ScreenRequest, current_user: dict = Depends(get_current_user)):
    """Screen for adverse media. Mandatory for Regular, optional for Simplified."""
    return screen_adverse_media(req.name, req.kyc_type)

@router.post("/exit-list/add", status_code=201)
async def exit_list_add(req: ExitListAddRequest, current_user: dict = Depends(get_current_user)):
    """Add a name to institution exit list. Admin action."""
    entry = add_to_exit_list(req.institution_id, req.name, req.reason)
    return {"success": True, "entry": entry}

@router.post("/exit-list/check")
async def exit_list_check(req: ExitListCheckRequest, current_user: dict = Depends(get_current_user)):
    """Check name against institution exit list."""
    return screen_exit_list(req.name, req.institution_id)

@router.post("/full")
async def full_screening(req: ScreenRequest, current_user: dict = Depends(get_current_user)):
    """
    Run all applicable screening checks based on eKYC type.
    SIMPLIFIED: UNSCR + Exit list
    REGULAR: UNSCR + PEP + Adverse media + Exit list
    Returns combined verdict: CLEAR | REVIEW | BLOCKED
    """
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    return run_full_screening(req.name, req.kyc_type, req.institution_id)

@router.get("/thresholds")
async def get_thresholds(current_user: dict = Depends(get_current_user)):
    """Return current screening match thresholds."""
    return {
        "unscr_exact_threshold":  1.0,
        "unscr_fuzzy_threshold":  UNSCR_FUZZY_MATCH_THRESHOLD,
        "pep_threshold":          PEP_MATCH_THRESHOLD,
        "screening_tiers": {
            "SIMPLIFIED": ["UNSCR", "EXIT_LIST"],
            "REGULAR":    ["UNSCR", "PEP", "ADVERSE_MEDIA", "EXIT_LIST"],
        },
        "bfiu_ref": "BFIU Circular No. 29 - Section 5",
    }
