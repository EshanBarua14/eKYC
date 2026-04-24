"""M60: EDD API Router — BFIU §4.2/§4.3"""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, CurrentUser
from app.db.models_edd import EDDStatus, EDDCase
from app.services import edd_service
from app.services.edd_service import EDDPermissionError, EDDStateError, EDDNotFoundError

router = APIRouter(prefix="/v1/edd", tags=["EDD §4.2/§4.3"])

class CreateEDDRequest(BaseModel):
    kyc_session_id: str
    customer_nid_hash: str
    trigger: str
    trigger_evidence: dict = Field(default_factory=dict)
    risk_score: int = 0
    is_existing_customer: bool = False
    assigned_to_user_id: Optional[uuid.UUID] = None

class AssignRequest(BaseModel):
    assign_to_user_id: uuid.UUID

class NotesRequest(BaseModel):
    notes: str = Field(..., min_length=1, max_length=2000)

class DecisionRequest(BaseModel):
    notes: str = Field(..., min_length=10, max_length=2000)

def _handle(e):
    if isinstance(e, EDDPermissionError): raise HTTPException(403, str(e))
    if isinstance(e, EDDStateError): raise HTTPException(409, str(e))
    if isinstance(e, EDDNotFoundError): raise HTTPException(404, str(e))
    raise e

@router.post("/cases", status_code=201)
def create_case(body: CreateEDDRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {"ADMIN", "COMPLIANCE_OFFICER"}: raise HTTPException(403, "Access denied")
    try:
        case = edd_service.create_edd_case(db, body.kyc_session_id, body.customer_nid_hash,
            body.trigger, body.trigger_evidence, body.risk_score,
            body.is_existing_customer, body.assigned_to_user_id)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "case_reference": case.case_reference, "status": case.status}

@router.get("/cases")
def list_cases(status_filter: Optional[str] = None, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    sf = status_filter.split(",") if status_filter else None
    cases = edd_service.get_edd_queue(db, actor_role=user.role, actor_user_id=user.id, status_filter=sf)
    return [{"case_id": str(c.id), "case_reference": c.case_reference, "status": c.status,
             "trigger": c.trigger, "risk_score": c.risk_score,
             "sla_deadline": c.sla_deadline.isoformat() if c.sla_deadline else None,
             "created_at": c.created_at.isoformat()} for c in cases]

@router.get("/cases/{case_id}")
def get_case(case_id: uuid.UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {"ADMIN","COMPLIANCE_OFFICER","AUDITOR"}: raise HTTPException(403, "Access denied")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise HTTPException(404, "Not found")
    return {"case_id": str(case.id), "case_reference": case.case_reference,
            "status": case.status, "trigger": case.trigger, "risk_score": case.risk_score,
            "sla_deadline": case.sla_deadline.isoformat() if case.sla_deadline else None,
            "decision_at": case.decision_at.isoformat() if case.decision_at else None,
            "decision_notes": case.decision_notes, "decision_role": case.decision_role,
            "actions": [{"action_type": a.action_type, "actor_role": a.actor_role,
                         "from_status": a.from_status, "to_status": a.to_status,
                         "notes": a.notes, "created_at": a.created_at.isoformat()} for a in case.actions]}

@router.post("/cases/{case_id}/assign")
def assign_case(case_id: uuid.UUID, body: AssignRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.assign_edd_case(db, case_id, user.id, user.role, body.assign_to_user_id)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status}

@router.post("/cases/{case_id}/request-info")
def req_info(case_id: uuid.UUID, body: NotesRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.request_info(db, case_id, user.id, user.role, body.notes)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status}

@router.post("/cases/{case_id}/start-review")
def start_rev(case_id: uuid.UUID, body: NotesRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.start_review(db, case_id, user.id, user.role, body.notes)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status}

@router.post("/cases/{case_id}/approve")
def approve(case_id: uuid.UUID, body: DecisionRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.approve_edd(db, case_id, user.id, user.role, body.notes)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status, "decision_at": case.decision_at.isoformat()}

@router.post("/cases/{case_id}/reject")
def reject(case_id: uuid.UUID, body: DecisionRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.reject_edd(db, case_id, user.id, user.role, body.notes)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status}

@router.post("/cases/{case_id}/immediate-close")
def imm_close(case_id: uuid.UUID, body: DecisionRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.immediate_close(db, case_id, user.id, user.role, body.notes)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status}

@router.post("/cases/{case_id}/escalate")
def escalate(case_id: uuid.UUID, body: DecisionRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try: case = edd_service.escalate_to_bfiu(db, case_id, user.id, user.role, body.notes)
    except Exception as e: _handle(e)
    return {"case_id": str(case.id), "status": case.status}
