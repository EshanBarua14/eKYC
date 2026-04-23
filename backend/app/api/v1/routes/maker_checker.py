"""
Xpert Fintech eKYC Platform
Maker-Checker Workflow Routes - M7
BFIU Circular No. 29 - dual-control requirement

POST /maker-checker/submit      - Maker submits action for approval
POST /maker-checker/decide      - Checker approves or rejects
GET  /maker-checker/pending     - List pending actions
GET  /maker-checker/action/{id} - Get action detail
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.maker_checker_service import (
    submit_maker_action, checker_decide,
    get_pending_actions, get_action,
    MAKER_CHECKER_OPERATIONS, SLA_HOURS,
)

router   = APIRouter(prefix="/maker-checker", tags=["Maker-Checker"])
security = HTTPBearer()

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
class SubmitActionRequest(BaseModel):
    operation:      str
    entity_id:      str
    entity_type:    str
    payload:        dict
    institution_id: str = "default"

class DecideRequest(BaseModel):
    action_id:    str
    decision:     str          # APPROVED | REJECTED
    note:         Optional[str] = None

# ---------------------------------------------------------------------------
# POST /maker-checker/submit
# ---------------------------------------------------------------------------
@router.post("/submit", status_code=201)
def submit_action(
    req: SubmitActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Maker submits a sensitive operation for checker approval."""
    result = submit_maker_action(
        operation      = req.operation,
        maker_id       = current_user["sub"],
        maker_role     = current_user.get("role", "MAKER"),
        entity_id      = req.entity_id,
        entity_type    = req.entity_type,
        payload        = req.payload,
        institution_id = req.institution_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result["error"])
    return result

# ---------------------------------------------------------------------------
# POST /maker-checker/decide
# ---------------------------------------------------------------------------
@router.post("/decide")
def decide_action(
    req: DecideRequest,
    current_user: dict = Depends(get_current_user),
):
    """Checker approves or rejects a pending maker action."""
    result = checker_decide(
        action_id    = req.action_id,
        checker_id   = current_user["sub"],
        checker_role = current_user.get("role", "CHECKER"),
        decision     = req.decision,
        note         = req.note,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result["error"])
    return result

# ---------------------------------------------------------------------------
# GET /maker-checker/pending
# ---------------------------------------------------------------------------
@router.get("/pending")
def list_pending(
    institution_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List all pending maker actions awaiting checker decision."""
    actions = get_pending_actions(institution_id)
    return {
        "pending_count": len(actions),
        "sla_hours":     SLA_HOURS,
        "actions":       actions,
        "bfiu_ref":      "BFIU Circular No. 29 - dual-control requirement",
    }

# ---------------------------------------------------------------------------
# GET /maker-checker/action/{action_id}
# ---------------------------------------------------------------------------
@router.get("/action/{action_id}")
def get_action_detail(
    action_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get detail of a pending or completed maker-checker action."""
    action = get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action

# ---------------------------------------------------------------------------
# GET /maker-checker/operations
# ---------------------------------------------------------------------------
@router.get("/operations")
def list_operations(current_user: dict = Depends(get_current_user)):
    """List all operations requiring maker-checker dual approval."""
    return {
        "operations": sorted(MAKER_CHECKER_OPERATIONS),
        "sla_hours":  SLA_HOURS,
        "bfiu_ref":   "BFIU Circular No. 29 - dual-control requirement",
    }
