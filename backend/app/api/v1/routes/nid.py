"""
Xpert Fintech eKYC Platform
NID Routes - M3
POST /nid/scan         - OCR scan NID card image
POST /nid/verify       - Verify NID against EC database
GET  /nid/session-status - Check attempt/session limits for an NID
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.session_limiter import (
    hash_nid, gate_attempt, increment_session_count,
    increment_attempt_count, check_session_limit,
    check_attempt_limit, reset_session, reset_nid_sessions,
)
from app.services.nid_ocr_service import scan_nid_card, validate_nid_number
from app.services.nid_api_client import lookup_nid, cross_match_nid

router   = APIRouter(prefix="/nid", tags=["NID Integration"])
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
class NIDScanRequest(BaseModel):
    front_image_b64: str
    back_image_b64:  Optional[str] = None
    session_id:      str

class NIDVerifyRequest(BaseModel):
    nid_number:  str
    session_id:  str
    ocr_fields:  Optional[dict] = None

class SessionStatusRequest(BaseModel):
    nid_number:  str
    session_id:  str

# ---------------------------------------------------------------------------
# POST /nid/scan
# ---------------------------------------------------------------------------
@router.post("/scan")
async def scan_nid(
    req: NIDScanRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Scan NID card image using Tesseract OCR.
    Extracts Bangla + English fields from NID card.
    Returns structured fields + NID hash + validity flag.
    """
    result = scan_nid_card(
        front_image_b64=req.front_image_b64,
        back_image_b64=req.back_image_b64,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": result.get("error_code", "IMAGE_DECODE_ERROR"),
                "message":    result.get("message", "Image processing failed"),
            }
        )

    return {
        "success":      True,
        "session_id":   req.session_id,
        "is_valid_nid": result["is_valid_nid"],
        "nid_format":   result["nid_format"],
        "nid_hash":     result["nid_hash"],
        "fields":       result["fields"],
        "ocr_mode":     result["ocr_mode"],
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    }

# ---------------------------------------------------------------------------
# POST /nid/verify
# ---------------------------------------------------------------------------
@router.post("/verify")
async def verify_nid(
    req: NIDVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Verify NID against EC database.
    Enforces BFIU session + attempt limits.
    Returns EC record + cross-match result.
    """
    # Validate NID format first
    nid_validation = validate_nid_number(req.nid_number)
    if not nid_validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_NID_FORMAT",
                "message":    f"Invalid NID number format: {req.nid_number}",
            }
        )

    # BFIU gate check
    gate = gate_attempt(req.nid_number, req.session_id)
    if not gate["allowed"]:
        status_code = 422
        raise HTTPException(
            status_code=status_code,
            detail={
                "error_code": gate["reason"],
                "message":    f"BFIU limit reached: {gate['reason']}",
                "details":    gate["details"],
            }
        )

    # Increment counters
    nid_hash = hash_nid(req.nid_number)
    increment_attempt_count(req.session_id)

    # Check if this is a new session (first attempt)
    attempt_count = check_attempt_limit(req.session_id)["current_count"]
    if attempt_count == 1:
        increment_session_count(nid_hash)

    # EC NID lookup
    ec_result = lookup_nid(req.nid_number)

    if not ec_result["found"]:
        error_code = ec_result.get("error_code", "NID_NOT_FOUND")
        if error_code == "NID_API_UNAVAILABLE":
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "NID_API_UNAVAILABLE",
                    "message":    "EC NID API is unavailable. Session queued.",
                }
            )
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "NID_NOT_FOUND",
                "message":    f"NID {req.nid_number} not found in EC database",
            }
        )

    # Cross-match OCR fields with EC record
    cross_match = {}
    if req.ocr_fields:
        cross_match = cross_match_nid(req.ocr_fields, ec_result["data"])

    session_status = check_session_limit(nid_hash)
    attempt_status = check_attempt_limit(req.session_id)

    return {
        "success":        True,
        "session_id":     req.session_id,
        "nid_hash":       nid_hash,
        "ec_source":      ec_result["source"],
        "ec_data":        ec_result["data"],
        "cross_match":    cross_match,
        "session_count":  session_status["current_count"],
        "attempt_count":  attempt_status["current_count"],
        "max_sessions":   session_status["max_count"],
        "max_attempts":   attempt_status["max_count"],
        "timestamp":      datetime.now(timezone.utc).isoformat(),
    }

# ---------------------------------------------------------------------------
# GET /nid/session-status
# ---------------------------------------------------------------------------
@router.get("/session-status")
async def session_status(
    nid_number: str,
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Check BFIU attempt and session limits for an NID.
    Returns current counts and whether further attempts are allowed.
    """
    nid_validation = validate_nid_number(nid_number)
    if not nid_validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_NID_FORMAT", "message": "Invalid NID format"}
        )

    nid_hash       = hash_nid(nid_number)
    session_check  = check_session_limit(nid_hash)
    attempt_check  = check_attempt_limit(session_id)

    return {
        "nid_hash":       nid_hash,
        "session_id":     session_id,
        "sessions_today": session_check["current_count"],
        "max_sessions":   session_check["max_count"],
        "session_allowed": session_check["allowed"],
        "attempts_used":  attempt_check["current_count"],
        "max_attempts":   attempt_check["max_count"],
        "attempt_allowed": attempt_check["allowed"],
        "retry_after":    session_check.get("retry_after"),
        "timestamp":      datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /nid/scan-ocr  (no auth — self-service customer portal)
# ---------------------------------------------------------------------------
class NIDOCRRequest(BaseModel):
    front_image_b64: str
    back_image_b64:  Optional[str] = None
    session_id:      str

@router.post("/scan-ocr")
async def scan_nid_ocr(req: NIDOCRRequest):
    """
    OCR scan NID card — no auth required for self-service portal.
    Returns structured fields extracted from front and back of NID card.
    """
    result = scan_nid_card(
        front_image_b64=req.front_image_b64,
        back_image_b64=req.back_image_b64,
    )

    if not result.get("success"):
        # Return empty fields rather than error — OCR failure is non-blocking
        return {
            "success":    False,
            "fields":     {},
            "is_valid_nid": False,
            "session_id": req.session_id,
            "error":      result.get("message", "OCR failed"),
        }

    return {
        "success":    True,
        "fields":     result.get("fields", {}),
        "is_valid_nid": result.get("is_valid_nid", False),
        "nid_format": result.get("nid_format"),
        "nid_hash":   result.get("nid_hash"),
        "session_id": req.session_id,
    }
