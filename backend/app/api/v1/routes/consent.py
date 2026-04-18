"""
Digital Consent Gate - M16
BFIU Circular No. 29 - Section 3.2
Mandatory digital consent before EC database query.

POST /consent/record     - Record consent with timestamp + IP
GET  /consent/{session_id} - Get consent record for a session
POST /consent/verify     - Check consent exists before EC query
GET  /consent/list       - List all consent records (admin/audit)
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/consent", tags=["Digital Consent"])

# ── in-memory store (PostgreSQL in prod) ───────────────────────────────────
_consents: dict = {}   # keyed by session_id

class ConsentRequest(BaseModel):
    session_id:     str
    nid_hash:       str
    institution_id: str = "N/A"
    agent_id:       str = "self-service"
    channel:        str = "SELF_SERVICE"   # SELF_SERVICE | AGENCY | BRANCH
    consent_text:   str = (
        "I hereby provide my explicit consent for this institution to verify "
        "my identity against the Bangladesh Election Commission (EC) NID database "
        "in accordance with BFIU Circular No. 29. I confirm that the information "
        "provided is accurate and authorise the retrieval of my demographic profile."
    )
    otp_verified:   bool = False
    ip_address:     Optional[str] = None
    user_agent:     Optional[str] = None

class ConsentVerifyRequest(BaseModel):
    session_id: str

@router.post("/record", status_code=201)
def record_consent(req: ConsentRequest, request: Request):
    """
    Record explicit digital consent before EC database query.
    BFIU mandates consent is captured and stored immutably.
    """
    if req.session_id in _consents:
        # Idempotent — return existing consent
        return {"consent": _consents[req.session_id], "already_recorded": True}

    consent_id = str(uuid.uuid4())
    now        = datetime.now(timezone.utc)

    # Capture IP from request if not provided
    ip = req.ip_address or request.client.host if request.client else "unknown"

    record = {
        "consent_id":     consent_id,
        "session_id":     req.session_id,
        "nid_hash":       req.nid_hash,
        "institution_id": req.institution_id,
        "agent_id":       req.agent_id,
        "channel":        req.channel,
        "consent_text":   req.consent_text,
        "otp_verified":   req.otp_verified,
        "ip_address":     ip,
        "user_agent":     req.user_agent,
        "timestamp":      now.isoformat(),
        "status":         "GRANTED",
        "bfiu_ref":       "BFIU Circular No. 29 - Section 3.2",
        "retention_years": 5,
    }
    _consents[req.session_id] = record
    return {"consent": record, "already_recorded": False}

@router.get("/{session_id}")
def get_consent(session_id: str):
    """Retrieve consent record for a session."""
    if session_id not in _consents:
        raise HTTPException(404, f"No consent record found for session '{session_id}'")
    return {"consent": _consents[session_id]}

@router.post("/verify")
def verify_consent(req: ConsentVerifyRequest):
    """
    Gate check — verify consent exists before allowing EC query.
    Returns 403 if consent not recorded.
    """
    if req.session_id not in _consents:
        raise HTTPException(
            403,
            detail={
                "error_code": "CONSENT_NOT_RECORDED",
                "message":    "Digital consent must be recorded before EC database query.",
                "bfiu_ref":   "BFIU Circular No. 29 - Section 3.2",
            }
        )
    c = _consents[req.session_id]
    if c["status"] != "GRANTED":
        raise HTTPException(
            403,
            detail={
                "error_code": "CONSENT_NOT_GRANTED",
                "message":    f"Consent status is {c['status']}. Must be GRANTED.",
            }
        )
    return {
        "consent_verified": True,
        "session_id":       req.session_id,
        "consent_id":       c["consent_id"],
        "timestamp":        c["timestamp"],
        "channel":          c["channel"],
    }

@router.post("/{session_id}/revoke")
def revoke_consent(session_id: str):
    """Revoke consent — blocks further EC queries for this session."""
    if session_id not in _consents:
        raise HTTPException(404, "Consent record not found")
    _consents[session_id]["status"] = "REVOKED"
    _consents[session_id]["revoked_at"] = datetime.now(timezone.utc).isoformat()
    return {"session_id": session_id, "status": "REVOKED"}

@router.get("/list/all")
def list_consents(limit: int = 50):
    """List all consent records for audit."""
    records = list(_consents.values())[-limit:]
    return {"consents": records, "total": len(_consents)}
