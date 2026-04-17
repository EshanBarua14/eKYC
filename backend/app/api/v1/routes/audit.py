"""
Xpert Fintech eKYC Platform
Audit Trail and Reporting Routes - M11
POST /audit/log            - Write audit log entry
GET  /audit/log            - Query audit log
GET  /audit/log/{id}       - Get single entry
GET  /audit/export/json    - Export as JSON
GET  /audit/export/csv     - Export as CSV
GET  /audit/dashboard      - Compliance dashboard stats
POST /audit/maker          - Submit maker action
POST /audit/checker/{id}   - Checker approve/reject
GET  /audit/pending        - List pending maker actions
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.audit_service import (
    log_event, get_entry, query_log,
    export_json, export_csv, get_dashboard_stats,
    AUDIT_EVENTS, RETENTION_YEARS,
)
from app.services.maker_checker_service import (
    submit_maker_action, checker_decide,
    get_pending_actions, get_action,
    MAKER_CHECKER_OPERATIONS, SLA_HOURS,
)

router   = APIRouter(prefix="/audit", tags=["Audit Trail"])
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

class LogEventRequest(BaseModel):
    event_type:     str
    entity_type:    str
    actor_id:       Optional[str]  = None
    actor_role:     Optional[str]  = None
    entity_id:      Optional[str]  = None
    session_id:     Optional[str]  = None
    ip_address:     Optional[str]  = None
    before_state:   Optional[dict] = None
    after_state:    Optional[dict] = None
    metadata:       Optional[dict] = None
    institution_id: Optional[str]  = None
    bfiu_ref:       Optional[str]  = None

class MakerActionRequest(BaseModel):
    operation:      str
    maker_id:       str
    maker_role:     str
    entity_id:      str
    entity_type:    str
    payload:        dict
    institution_id: str

class CheckerDecisionRequest(BaseModel):
    checker_id:   str
    checker_role: str
    decision:     str
    note:         Optional[str] = None

@router.post("/log", status_code=201)
def write_log(req: LogEventRequest, current_user: dict = Depends(get_current_user)):
    """Write an immutable audit log entry."""
    try:
        entry = log_event(
            event_type=req.event_type, entity_type=req.entity_type,
            actor_id=req.actor_id, actor_role=req.actor_role,
            entity_id=req.entity_id, session_id=req.session_id,
            ip_address=req.ip_address, before_state=req.before_state,
            after_state=req.after_state, metadata=req.metadata,
            institution_id=req.institution_id, bfiu_ref=req.bfiu_ref,
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get("/log")
def query_audit_log(
    event_type:     Optional[str] = Query(None),
    entity_type:    Optional[str] = Query(None),
    actor_id:       Optional[str] = Query(None),
    institution_id: Optional[str] = Query(None),
    session_id:     Optional[str] = Query(None),
    limit:          int = Query(100, ge=1, le=1000),
    offset:         int = Query(0, ge=0),
    current_user:   dict = Depends(get_current_user),
):
    """Query audit log with optional filters."""
    return query_log(
        event_type=event_type, entity_type=entity_type,
        actor_id=actor_id, institution_id=institution_id,
        session_id=session_id, limit=limit, offset=offset,
    )

@router.get("/log/{entry_id}")
def get_log_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single audit log entry by ID."""
    entry = get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry

@router.get("/export/json")
def export_audit_json(
    institution_id: Optional[str] = Query(None),
    current_user:   dict = Depends(get_current_user),
):
    """Export audit log as BFIU-ready JSON."""
    return PlainTextResponse(
        export_json(institution_id),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=bfiu_audit_export.json"},
    )

@router.get("/export/csv")
def export_audit_csv(
    institution_id: Optional[str] = Query(None),
    current_user:   dict = Depends(get_current_user),
):
    """Export audit log as CSV."""
    return PlainTextResponse(
        export_csv(institution_id),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bfiu_audit_export.csv"},
    )

@router.get("/dashboard")
def compliance_dashboard(
    institution_id: Optional[str] = Query(None),
    current_user:   dict = Depends(get_current_user),
):
    """Compliance dashboard stats."""
    return get_dashboard_stats(institution_id)

@router.get("/events")
def list_event_types(current_user: dict = Depends(get_current_user)):
    """List all valid audit event types."""
    return {
        "event_types":     sorted(AUDIT_EVENTS),
        "total":           len(AUDIT_EVENTS),
        "retention_years": RETENTION_YEARS,
        "bfiu_ref":        "BFIU Circular No. 29 - Section 5.1",
    }

@router.post("/maker", status_code=201)
def maker_submit(req: MakerActionRequest, current_user: dict = Depends(get_current_user)):
    """Submit a sensitive action for checker approval."""
    result = submit_maker_action(
        req.operation, req.maker_id, req.maker_role,
        req.entity_id, req.entity_type, req.payload, req.institution_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result

@router.post("/checker/{action_id}")
def checker_action(
    action_id: str,
    req: CheckerDecisionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Checker approves or rejects a pending maker action."""
    result = checker_decide(action_id, req.checker_id, req.checker_role, req.decision, req.note)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result

@router.get("/pending")
def list_pending(
    institution_id: Optional[str] = Query(None),
    current_user:   dict = Depends(get_current_user),
):
    """List pending maker actions awaiting checker decision."""
    return {
        "pending": get_pending_actions(institution_id),
        "sla_hours": SLA_HOURS,
    }

@router.get("/policy")
def audit_policy(current_user: dict = Depends(get_current_user)):
    """Return audit and retention policy."""
    return {
        "retention_years":          RETENTION_YEARS,
        "log_is_immutable":         True,
        "maker_checker_operations": sorted(MAKER_CHECKER_OPERATIONS),
        "maker_checker_sla_hours":  SLA_HOURS,
        "export_formats":           ["JSON", "CSV"],
        "bfiu_ref":                 "BFIU Circular No. 29 - Section 5.1",
    }
