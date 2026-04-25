"""
M60: EDD API Router
BFIU Circular No. 29 §4.2, §4.3

Endpoints:
  POST   /v1/edd/cases                    — create EDD case (system/ADMIN)
  GET    /v1/edd/cases                    — list EDD queue (CO/ADMIN)
  GET    /v1/edd/cases/{case_id}          — get single case
  POST   /v1/edd/cases/{case_id}/assign   — assign to CO (ADMIN/CO)
  POST   /v1/edd/cases/{case_id}/request-info
  POST   /v1/edd/cases/{case_id}/start-review
  POST   /v1/edd/cases/{case_id}/approve  — CO ONLY
  POST   /v1/edd/cases/{case_id}/reject   — CO ONLY
  POST   /v1/edd/cases/{case_id}/immediate-close — CO ONLY (§4.3 irregular)
  POST   /v1/edd/cases/{case_id}/escalate — CO ONLY
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, CurrentUser
from app.db.models_edd import EDDStatus
from app.services import edd_service
from app.services.edd_service import (
    EDDPermissionError, EDDStateError, EDDNotFoundError,
)

router = APIRouter(prefix="/v1/edd", tags=["EDD — §4.2/§4.3"])


# ─────────────────────────── Schemas ─────────────────────────────────────────
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
    notes: str = Field(..., min_length=10, max_length=2000,
                       description="Mandatory justification for BFIU audit trail")


# ─────────────────────────── Helpers ─────────────────────────────────────────
def _handle_edd_errors(e: Exception) -> None:
    if isinstance(e, EDDPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    if isinstance(e, EDDStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if isinstance(e, EDDNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    raise e


# ─────────────────────────── Endpoints ───────────────────────────────────────
@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(
    body: CreateEDDRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create EDD case. ADMIN or SYSTEM (internal workflow calls) only."""
    if user.role not in {"ADMIN", "COMPLIANCE_OFFICER"}:
        raise HTTPException(403, "Only ADMIN/COMPLIANCE_OFFICER can create EDD cases")
    try:
        case = edd_service.create_edd_case(
            db,
            kyc_session_id=body.kyc_session_id,
            customer_nid_hash=body.customer_nid_hash,
            trigger=body.trigger,
            trigger_evidence=body.trigger_evidence,
            risk_score=body.risk_score,
            is_existing_customer=body.is_existing_customer,
            assigned_to_user_id=body.assigned_to_user_id,
        )
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "case_reference": case.case_reference, "status": case.status}


@router.get("/cases")
def list_cases(
    status_filter: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    EDD queue.
    COMPLIANCE_OFFICER: own assigned + unassigned OPEN cases.
    ADMIN: all cases.
    """
    sf = status_filter.split(",") if status_filter else None
    cases = edd_service.get_edd_queue(
        db, actor_role=user.role, actor_user_id=user.id, status_filter=sf
    )
    return [
        {
            "case_id": str(c.id),
            "case_reference": c.case_reference,
            "kyc_session_id": c.kyc_session_id,
            "trigger": c.trigger,
            "risk_score": c.risk_score,
            "status": c.status,
            "sla_deadline": c.sla_deadline.isoformat() if c.sla_deadline else None,
            "assigned_to": str(c.assigned_to_user_id) if c.assigned_to_user_id else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in cases
    ]


@router.get("/cases/{case_id}")
def get_case(
    case_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in {"ADMIN", "COMPLIANCE_OFFICER", "AUDITOR"}:
        raise HTTPException(403, "Access denied")
    case = db.query(edd_service.EDDCase).filter(edd_service.EDDCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "EDD case not found")
    return {
        "case_id": str(case.id),
        "case_reference": case.case_reference,
        "kyc_session_id": case.kyc_session_id,
        "customer_nid_hash": case.customer_nid_hash,
        "trigger": case.trigger,
        "trigger_evidence": case.trigger_evidence,
        "risk_score": case.risk_score,
        "status": case.status,
        "is_existing_customer": case.is_existing_customer,
        "sla_deadline": case.sla_deadline.isoformat() if case.sla_deadline else None,
        "assigned_to": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
        "decision_at": case.decision_at.isoformat() if case.decision_at else None,
        "decision_notes": case.decision_notes,
        "decision_role": case.decision_role,
        "created_at": case.created_at.isoformat(),
        "actions": [
            {
                "action_type": a.action_type,
                "actor_role": a.actor_role,
                "from_status": a.from_status,
                "to_status": a.to_status,
                "notes": a.notes,
                "created_at": a.created_at.isoformat(),
            }
            for a in case.actions
        ],
    }


@router.post("/cases/{case_id}/assign")
def assign_case(
    case_id: uuid.UUID,
    body: AssignRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        case = edd_service.assign_edd_case(
            db, case_id, user.id, user.role, body.assign_to_user_id
        )
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "status": case.status, "assigned_to": str(case.assigned_to_user_id)}


@router.post("/cases/{case_id}/request-info")
def request_info(
    case_id: uuid.UUID,
    body: NotesRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        case = edd_service.request_info(db, case_id, user.id, user.role, body.notes)
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/start-review")
def start_review(
    case_id: uuid.UUID,
    body: NotesRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        case = edd_service.start_review(db, case_id, user.id, user.role, body.notes)
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/approve")
def approve(
    case_id: uuid.UUID,
    body: DecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    COMPLIANCE_OFFICER ONLY — BFIU §4.3.
    CHECKER is BLOCKED (HTTP 403).
    """
    try:
        case = edd_service.approve_edd(db, case_id, user.id, user.role, body.notes)
    except Exception as e:
        _handle_edd_errors(e)
    return {
        "case_id": str(case.id),
        "case_reference": case.case_reference,
        "status": case.status,
        "decision_at": case.decision_at.isoformat(),
        "bfiu_ref": "BFIU Circular No. 29 §4.2/§4.3",
    }


@router.post("/cases/{case_id}/reject")
def reject(
    case_id: uuid.UUID,
    body: DecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """COMPLIANCE_OFFICER ONLY — BFIU §4.3."""
    try:
        case = edd_service.reject_edd(db, case_id, user.id, user.role, body.notes)
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/immediate-close")
def immediate_close(
    case_id: uuid.UUID,
    body: DecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    COMPLIANCE_OFFICER ONLY.
    BFIU §4.3: immediate closure for irregular activity.
    """
    try:
        case = edd_service.immediate_close(db, case_id, user.id, user.role, body.notes)
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/escalate")
def escalate(
    case_id: uuid.UUID,
    body: DecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """COMPLIANCE_OFFICER ONLY — escalate to BFIU."""
    try:
        case = edd_service.escalate_to_bfiu(db, case_id, user.id, user.role, body.notes)
    except Exception as e:
        _handle_edd_errors(e)
    return {"case_id": str(case.id), "status": case.status}
