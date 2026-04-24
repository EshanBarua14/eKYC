"""
M60: EDD Service — BFIU §4.2, §4.3
CHECKER is explicitly blocked from EDD approval.
Only COMPLIANCE_OFFICER can approve/reject/close EDD cases.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.core.timezone import now_bst as bst_now
from app.db.models_edd import EDDCase, EDDAction, EDDActionType, EDDStatus, EDDTrigger

ALLOWED_EDD_ROLES = {"COMPLIANCE_OFFICER", "ADMIN"}
BLOCKED_EDD_APPROVAL_ROLES = {"CHECKER", "MAKER", "AGENT", "AUDITOR"}
EDD_SLA_DAYS = 30
_CASE_REF_PREFIX = "EDD"

class EDDPermissionError(Exception): pass
class EDDStateError(Exception): pass
class EDDNotFoundError(Exception): pass

def _require_compliance_officer(actor_role: str, action: str) -> None:
    if actor_role in BLOCKED_EDD_APPROVAL_ROLES:
        raise EDDPermissionError(
            f"Role '{actor_role}' is not permitted to '{action}' EDD cases. "
            f"BFIU §4.3 requires Chief AML/CFT Compliance Officer approval. "
            f"Required role: COMPLIANCE_OFFICER"
        )
    if actor_role not in ALLOWED_EDD_ROLES:
        raise EDDPermissionError(f"Unknown role '{actor_role}'. EDD actions require COMPLIANCE_OFFICER.")

def _gen_case_reference(db: Session) -> str:
    year = bst_now().year
    count = db.query(EDDCase).filter(EDDCase.case_reference.like(f"{_CASE_REF_PREFIX}-{year}-%")).count()
    return f"{_CASE_REF_PREFIX}-{year}-{count + 1:05d}"

def _append_action(db, case, action_type, actor_user_id, actor_role, from_status, to_status, notes=None, metadata=None):
    action = EDDAction(
        case_id=case.id, action_type=action_type,
        actor_user_id=actor_user_id, actor_role=actor_role,
        from_status=from_status, to_status=to_status,
        notes=notes, metadata_=metadata or {},
    )
    db.add(action)
    return action

def create_edd_case(db, kyc_session_id, customer_nid_hash, trigger, trigger_evidence, risk_score, is_existing_customer=False, assigned_to_user_id=None):
    now = bst_now()
    sla_deadline = now + timedelta(days=EDD_SLA_DAYS) if is_existing_customer else None
    case = EDDCase(
        case_reference=_gen_case_reference(db),
        kyc_session_id=kyc_session_id, customer_nid_hash=customer_nid_hash,
        trigger=trigger, trigger_evidence=trigger_evidence, risk_score=risk_score,
        status=EDDStatus.OPEN, is_existing_customer=is_existing_customer,
        sla_deadline=sla_deadline, assigned_to_user_id=assigned_to_user_id,
        assigned_at=now if assigned_to_user_id else None,
    )
    db.add(case)
    db.flush()
    _append_action(db, case, EDDActionType.CASE_CREATED, None, "SYSTEM", None, EDDStatus.OPEN,
        notes=f"EDD triggered: {trigger}",
        metadata={"trigger": trigger, "risk_score": risk_score, "kyc_session_id": kyc_session_id,
                  "sla_deadline": sla_deadline.isoformat() if sla_deadline else None,
                  "bfiu_ref": "BFIU Circular No. 29 §4.2/§4.3"})
    db.commit()
    db.refresh(case)
    return case

def assign_edd_case(db, case_id, actor_user_id, actor_role, assign_to_user_id):
    if actor_role not in {"ADMIN", "COMPLIANCE_OFFICER"}:
        raise EDDPermissionError(f"Role '{actor_role}' cannot assign EDD cases.")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Cannot reassign terminal case: {case.status}")
    case.assigned_to_user_id = assign_to_user_id
    case.assigned_at = bst_now()
    _append_action(db, case, EDDActionType.ASSIGNED, actor_user_id, actor_role, case.status, case.status, "Reassigned")
    db.commit(); db.refresh(case); return case

def request_info(db, case_id, actor_user_id, actor_role, notes):
    _require_compliance_officer(actor_role, "request_info")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Case closed: {case.status}")
    prev = case.status; case.status = EDDStatus.INFO_REQUESTED
    _append_action(db, case, EDDActionType.INFO_REQUESTED, actor_user_id, actor_role, prev, EDDStatus.INFO_REQUESTED, notes)
    db.commit(); db.refresh(case); return case

def start_review(db, case_id, actor_user_id, actor_role, notes=None):
    _require_compliance_officer(actor_role, "start_review")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Case closed: {case.status}")
    prev = case.status; case.status = EDDStatus.UNDER_REVIEW
    _append_action(db, case, EDDActionType.STATUS_CHANGED, actor_user_id, actor_role, prev, EDDStatus.UNDER_REVIEW, notes or "Review started")
    db.commit(); db.refresh(case); return case

def approve_edd(db, case_id, actor_user_id, actor_role, notes):
    _require_compliance_officer(actor_role, "approve")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Cannot approve terminal case: {case.status}")
    now = bst_now(); prev = case.status
    case.status = EDDStatus.APPROVED
    case.decision_user_id = actor_user_id; case.decision_role = actor_role
    case.decision_at = now; case.decision_notes = notes
    _append_action(db, case, EDDActionType.APPROVED, actor_user_id, actor_role, prev, EDDStatus.APPROVED, notes,
        metadata={"bfiu_ref": "BFIU Circular No. 29 §4.2/§4.3", "decision_at_bst": now.isoformat()})
    db.commit(); db.refresh(case); return case

def reject_edd(db, case_id, actor_user_id, actor_role, notes):
    _require_compliance_officer(actor_role, "reject")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Cannot reject terminal case: {case.status}")
    now = bst_now(); prev = case.status
    case.status = EDDStatus.REJECTED
    case.decision_user_id = actor_user_id; case.decision_role = actor_role
    case.decision_at = now; case.decision_notes = notes
    _append_action(db, case, EDDActionType.REJECTED, actor_user_id, actor_role, prev, EDDStatus.REJECTED, notes)
    db.commit(); db.refresh(case); return case

def immediate_close(db, case_id, actor_user_id, actor_role, notes):
    _require_compliance_officer(actor_role, "immediate_close")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Already closed: {case.status}")
    now = bst_now(); prev = case.status
    case.status = EDDStatus.REJECTED
    case.decision_user_id = actor_user_id; case.decision_role = actor_role
    case.decision_at = now; case.decision_notes = f"IMMEDIATE CLOSE: {notes}"
    _append_action(db, case, EDDActionType.REJECTED, actor_user_id, actor_role, prev, EDDStatus.REJECTED,
        f"Immediate closure — irregular activity: {notes}",
        metadata={"immediate_close": True, "bfiu_ref": "BFIU §4.3 — irregular activity immediate closure"})
    db.commit(); db.refresh(case); return case

def escalate_to_bfiu(db, case_id, actor_user_id, actor_role, notes):
    _require_compliance_officer(actor_role, "escalate")
    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case: raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL: raise EDDStateError(f"Already terminal: {case.status}")
    now = bst_now(); prev = case.status
    case.status = EDDStatus.ESCALATED
    case.decision_user_id = actor_user_id; case.decision_role = actor_role
    case.decision_at = now; case.decision_notes = notes
    _append_action(db, case, EDDActionType.ESCALATED_TO_BFIU, actor_user_id, actor_role, prev, EDDStatus.ESCALATED, notes)
    db.commit(); db.refresh(case); return case

def auto_close_expired_cases(db):
    now = bst_now()
    expired = db.query(EDDCase).filter(
        EDDCase.status.in_(list(EDDStatus.ACTIVE)),
        EDDCase.sla_deadline.isnot(None),
        EDDCase.sla_deadline <= now,
    ).all()
    closed = 0
    for case in expired:
        prev = case.status; case.status = EDDStatus.AUTO_CLOSED
        case.decision_at = now
        case.decision_notes = "Auto-closed: SLA deadline breached (BFIU §4.3 1-month window)"
        _append_action(db, case, EDDActionType.AUTO_CLOSED, None, "SYSTEM", prev, EDDStatus.AUTO_CLOSED,
            "SLA deadline breached",
            metadata={"sla_deadline": case.sla_deadline.isoformat(), "closed_at": now.isoformat(),
                      "bfiu_ref": "BFIU §4.3 — 1-month auto-close"})
        closed += 1
    if closed: db.commit()
    return closed

def send_sla_warnings(db, warn_days_before=7):
    now = bst_now(); warn_cutoff = now + timedelta(days=warn_days_before)
    near_deadline = db.query(EDDCase).filter(
        EDDCase.status.in_(list(EDDStatus.ACTIVE)),
        EDDCase.sla_deadline.isnot(None),
        EDDCase.sla_deadline <= warn_cutoff,
        EDDCase.sla_deadline > now,
    ).all()
    warned = 0
    for case in near_deadline:
        recent_warn = db.query(EDDAction).filter(
            EDDAction.case_id == case.id,
            EDDAction.action_type == EDDActionType.SLA_WARNING,
            EDDAction.created_at >= now - timedelta(hours=24),
        ).first()
        if recent_warn: continue
        _append_action(db, case, EDDActionType.SLA_WARNING, None, "SYSTEM", case.status, case.status,
            f"SLA deadline in {warn_days_before} days",
            metadata={"sla_deadline": case.sla_deadline.isoformat(), "days_remaining": (case.sla_deadline - now).days})
        warned += 1
    if warned: db.commit()
    return warned

def get_edd_queue(db, actor_role, actor_user_id=None, status_filter=None):
    if actor_role not in ALLOWED_EDD_ROLES: return []
    q = db.query(EDDCase)
    if status_filter: q = q.filter(EDDCase.status.in_(status_filter))
    if actor_role == "COMPLIANCE_OFFICER" and actor_user_id:
        from sqlalchemy import or_
        q = q.filter(or_(EDDCase.assigned_to_user_id == actor_user_id, EDDCase.status == EDDStatus.OPEN))
    return q.order_by(EDDCase.sla_deadline.asc().nullslast(), EDDCase.created_at.asc()).all()
