"""
M60: EDD Service
BFIU Circular No. 29 §4.2, §4.3

Rules enforced:
- Only COMPLIANCE_OFFICER can approve/reject/close EDD cases
- CHECKER is explicitly BLOCKED from EDD approval
- EDD cases auto-close after 1-month SLA (existing customers)
- Irregular activity → immediate closure available to CO
- All actions logged with BST timestamps
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.timezone import bst_now
from app.db.models_edd import (
    EDDCase, EDDAction, EDDActionType, EDDStatus, EDDTrigger,
)

# ── BFIU §4.2/§4.3 Role Constants ─────────────────────────────────────────────
ALLOWED_EDD_ROLES = {"COMPLIANCE_OFFICER", "ADMIN"}
BLOCKED_EDD_APPROVAL_ROLES = {"CHECKER", "MAKER", "AGENT", "AUDITOR"}

# 1 calendar month SLA for existing customers (§4.3)
EDD_SLA_DAYS = 30

# Counter prefix for case reference generation
_CASE_REF_PREFIX = "EDD"


class EDDPermissionError(Exception):
    """Raised when a non-CO role attempts an EDD action."""


class EDDStateError(Exception):
    """Raised when action is invalid for current EDD state."""


class EDDNotFoundError(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────────
def _gen_case_reference(db: Session) -> str:
    """Generate human-readable reference like EDD-2026-00042."""
    year = bst_now().year
    count = db.query(EDDCase).filter(
        EDDCase.case_reference.like(f"{_CASE_REF_PREFIX}-{year}-%")
    ).count()
    return f"{_CASE_REF_PREFIX}-{year}-{count + 1:05d}"


def _require_compliance_officer(actor_role: str, action: str) -> None:
    """
    BFIU §4.3: Chief AML/CFT Compliance Officer must personally take EDD decisions.
    CHECKER is explicitly blocked — they handle standard verifications only.
    """
    if actor_role in BLOCKED_EDD_APPROVAL_ROLES:
        raise EDDPermissionError(
            f"Role '{actor_role}' is not permitted to '{action}' EDD cases. "
            f"BFIU §4.3 requires Chief AML/CFT Compliance Officer approval. "
            f"Required role: COMPLIANCE_OFFICER"
        )
    if actor_role not in ALLOWED_EDD_ROLES:
        raise EDDPermissionError(
            f"Unknown role '{actor_role}'. EDD actions require COMPLIANCE_OFFICER."
        )


def _append_action(
    db: Session,
    case: EDDCase,
    action_type: str,
    actor_user_id: Optional[uuid.UUID],
    actor_role: Optional[str],
    from_status: Optional[str],
    to_status: Optional[str],
    notes: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> EDDAction:
    action = EDDAction(
        case_id=case.id,
        action_type=action_type,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=from_status,
        to_status=to_status,
        notes=notes,
        metadata_=metadata or {},
    )
    db.add(action)
    return action


# ─────────────────────────── Public API ──────────────────────────────────────

def create_edd_case(
    db: Session,
    kyc_session_id: str,
    customer_nid_hash: str,
    trigger: str,
    trigger_evidence: dict,
    risk_score: int,
    is_existing_customer: bool = False,
    assigned_to_user_id: Optional[uuid.UUID] = None,
) -> EDDCase:
    """
    Create EDD case. Called by KYC workflow engine when:
    - risk_score >= 15 (§4.2)
    - PEP/IP flag set (§4.2)
    - Adverse media flag (§5.3)
    - Irregular activity detected (§4.3)
    """
    now = bst_now()

    sla_deadline = None
    if is_existing_customer:
        # BFIU §4.3: 1-month window for existing customers
        sla_deadline = now + timedelta(days=EDD_SLA_DAYS)

    case = EDDCase(
        case_reference=_gen_case_reference(db),
        kyc_session_id=kyc_session_id,
        customer_nid_hash=customer_nid_hash,
        trigger=trigger,
        trigger_evidence=trigger_evidence,
        risk_score=risk_score,
        status=EDDStatus.OPEN,
        is_existing_customer=is_existing_customer,
        sla_deadline=sla_deadline,
        assigned_to_user_id=assigned_to_user_id,
        assigned_at=now if assigned_to_user_id else None,
    )
    db.add(case)
    db.flush()

    _append_action(
        db, case,
        action_type=EDDActionType.CASE_CREATED,
        actor_user_id=None,
        actor_role="SYSTEM",
        from_status=None,
        to_status=EDDStatus.OPEN,
        notes=f"EDD triggered: {trigger}",
        metadata={
            "trigger": trigger,
            "risk_score": risk_score,
            "kyc_session_id": kyc_session_id,
            "sla_deadline": sla_deadline.isoformat() if sla_deadline else None,
            "bfiu_ref": "BFIU Circular No. 29 §4.2/§4.3",
        },
    )

    if assigned_to_user_id:
        _append_action(
            db, case,
            action_type=EDDActionType.ASSIGNED,
            actor_user_id=None,
            actor_role="SYSTEM",
            from_status=EDDStatus.OPEN,
            to_status=EDDStatus.OPEN,
            notes="Auto-assigned to Compliance Officer",
            metadata={"assigned_to": str(assigned_to_user_id)},
        )

    db.commit()
    db.refresh(case)
    return case


def assign_edd_case(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    assign_to_user_id: uuid.UUID,
) -> EDDCase:
    """Assign/reassign EDD case to a Compliance Officer. ADMIN only."""
    if actor_role not in {"ADMIN", "COMPLIANCE_OFFICER"}:
        raise EDDPermissionError(f"Role '{actor_role}' cannot assign EDD cases.")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(f"EDD case {case_id} not found")
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"Cannot reassign terminal EDD case (status={case.status})")

    prev = case.assigned_to_user_id
    case.assigned_to_user_id = assign_to_user_id
    case.assigned_at = bst_now()

    _append_action(
        db, case,
        action_type=EDDActionType.ASSIGNED,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=case.status,
        to_status=case.status,
        notes="Case reassigned",
        metadata={"from_user": str(prev), "to_user": str(assign_to_user_id)},
    )
    db.commit()
    db.refresh(case)
    return case


def request_info(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    notes: str,
) -> EDDCase:
    """CO requests additional information from customer (§4.3)."""
    _require_compliance_officer(actor_role, "request_info")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(f"EDD case {case_id} not found")
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"EDD case already closed (status={case.status})")

    prev = case.status
    case.status = EDDStatus.INFO_REQUESTED

    _append_action(
        db, case,
        action_type=EDDActionType.INFO_REQUESTED,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=prev,
        to_status=EDDStatus.INFO_REQUESTED,
        notes=notes,
        metadata={"bfiu_ref": "BFIU §4.3 — additional information request"},
    )
    db.commit()
    db.refresh(case)
    return case


def start_review(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    notes: Optional[str] = None,
) -> EDDCase:
    """CO marks case as under active review."""
    _require_compliance_officer(actor_role, "start_review")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"Case already closed: {case.status}")

    prev = case.status
    case.status = EDDStatus.UNDER_REVIEW

    _append_action(
        db, case,
        action_type=EDDActionType.STATUS_CHANGED,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=prev,
        to_status=EDDStatus.UNDER_REVIEW,
        notes=notes or "Review started",
    )
    db.commit()
    db.refresh(case)
    return case


def approve_edd(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    notes: str,
) -> EDDCase:
    """
    CO approves EDD case — customer account proceeds.
    BFIU §4.3: ONLY COMPLIANCE_OFFICER can approve.
    CHECKER is explicitly blocked.
    """
    _require_compliance_officer(actor_role, "approve")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"Cannot approve terminal case: {case.status}")

    now = bst_now()
    prev = case.status
    case.status = EDDStatus.APPROVED
    case.decision_user_id = actor_user_id
    case.decision_role = actor_role
    case.decision_at = now
    case.decision_notes = notes

    _append_action(
        db, case,
        action_type=EDDActionType.APPROVED,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=prev,
        to_status=EDDStatus.APPROVED,
        notes=notes,
        metadata={
            "bfiu_ref": "BFIU Circular No. 29 §4.2 — EDD approval by Chief AML/CFT CO",
            "decision_at_bst": now.isoformat(),
        },
    )
    db.commit()
    db.refresh(case)
    return case


def reject_edd(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    notes: str,
) -> EDDCase:
    """CO rejects EDD case — account rejected/closed."""
    _require_compliance_officer(actor_role, "reject")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"Cannot reject terminal case: {case.status}")

    now = bst_now()
    prev = case.status
    case.status = EDDStatus.REJECTED
    case.decision_user_id = actor_user_id
    case.decision_role = actor_role
    case.decision_at = now
    case.decision_notes = notes

    _append_action(
        db, case,
        action_type=EDDActionType.REJECTED,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=prev,
        to_status=EDDStatus.REJECTED,
        notes=notes,
        metadata={"bfiu_ref": "BFIU Circular No. 29 §4.3"},
    )
    db.commit()
    db.refresh(case)
    return case


def immediate_close(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    notes: str,
) -> EDDCase:
    """
    BFIU §4.3: Immediate closure for irregular activity.
    Only COMPLIANCE_OFFICER can invoke this.
    """
    _require_compliance_officer(actor_role, "immediate_close")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"Already closed: {case.status}")

    now = bst_now()
    prev = case.status
    case.status = EDDStatus.REJECTED
    case.decision_user_id = actor_user_id
    case.decision_role = actor_role
    case.decision_at = now
    case.decision_notes = f"IMMEDIATE CLOSE: {notes}"

    _append_action(
        db, case,
        action_type=EDDActionType.REJECTED,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=prev,
        to_status=EDDStatus.REJECTED,
        notes=f"Immediate closure — irregular activity: {notes}",
        metadata={
            "immediate_close": True,
            "bfiu_ref": "BFIU §4.3 — irregular activity immediate closure",
        },
    )
    db.commit()
    db.refresh(case)
    return case


def escalate_to_bfiu(
    db: Session,
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    notes: str,
) -> EDDCase:
    """CO escalates case to BFIU directly."""
    _require_compliance_officer(actor_role, "escalate")

    case = db.query(EDDCase).filter(EDDCase.id == case_id).first()
    if not case:
        raise EDDNotFoundError(str(case_id))
    if case.status in EDDStatus.TERMINAL:
        raise EDDStateError(f"Already in terminal state: {case.status}")

    now = bst_now()
    prev = case.status
    case.status = EDDStatus.ESCALATED
    case.decision_user_id = actor_user_id
    case.decision_role = actor_role
    case.decision_at = now
    case.decision_notes = notes

    _append_action(
        db, case,
        action_type=EDDActionType.ESCALATED_TO_BFIU,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=prev,
        to_status=EDDStatus.ESCALATED,
        notes=notes,
        metadata={"bfiu_ref": "BFIU §4.3 — escalation to BFIU"},
    )
    db.commit()
    db.refresh(case)
    return case


def auto_close_expired_cases(db: Session) -> int:
    """
    Celery beat task: auto-close EDD cases past SLA deadline.
    BFIU §4.3: 1-month window → auto-close if CO hasn't acted.
    Returns count of closed cases.
    """
    now = bst_now()
    expired = db.query(EDDCase).filter(
        EDDCase.status.in_(list(EDDStatus.ACTIVE)),
        EDDCase.sla_deadline.isnot(None),
        EDDCase.sla_deadline <= now,
    ).all()

    closed = 0
    for case in expired:
        prev = case.status
        case.status = EDDStatus.AUTO_CLOSED
        case.decision_at = now
        case.decision_notes = "Auto-closed: SLA deadline breached (BFIU §4.3 1-month window)"

        _append_action(
            db, case,
            action_type=EDDActionType.AUTO_CLOSED,
            actor_user_id=None,
            actor_role="SYSTEM",
            from_status=prev,
            to_status=EDDStatus.AUTO_CLOSED,
            notes="SLA deadline breached",
            metadata={
                "sla_deadline": case.sla_deadline.isoformat(),
                "closed_at": now.isoformat(),
                "bfiu_ref": "BFIU §4.3 — 1-month auto-close",
            },
        )
        closed += 1

    if closed:
        db.commit()
    return closed


def send_sla_warnings(db: Session, warn_days_before: int = 7) -> int:
    """
    Celery beat task: warn CO when SLA deadline is approaching.
    Returns count of warnings logged.
    """
    now = bst_now()
    warn_cutoff = now + timedelta(days=warn_days_before)

    near_deadline = db.query(EDDCase).filter(
        EDDCase.status.in_(list(EDDStatus.ACTIVE)),
        EDDCase.sla_deadline.isnot(None),
        EDDCase.sla_deadline <= warn_cutoff,
        EDDCase.sla_deadline > now,
    ).all()

    warned = 0
    for case in near_deadline:
        # Check no warning logged in last 24h to avoid spam
        recent_warn = db.query(EDDAction).filter(
            EDDAction.case_id == case.id,
            EDDAction.action_type == EDDActionType.SLA_WARNING,
            EDDAction.created_at >= now - timedelta(hours=24),
        ).first()
        if recent_warn:
            continue

        _append_action(
            db, case,
            action_type=EDDActionType.SLA_WARNING,
            actor_user_id=None,
            actor_role="SYSTEM",
            from_status=case.status,
            to_status=case.status,
            notes=f"SLA deadline in {warn_days_before} days",
            metadata={
                "sla_deadline": case.sla_deadline.isoformat(),
                "days_remaining": (case.sla_deadline - now).days,
            },
        )
        warned += 1

    if warned:
        db.commit()
    return warned


def get_edd_queue(
    db: Session,
    actor_role: str,
    actor_user_id: Optional[uuid.UUID] = None,
    status_filter: Optional[list[str]] = None,
) -> list[EDDCase]:
    """
    Fetch EDD queue.
    COMPLIANCE_OFFICER: sees own assigned cases + unassigned OPEN cases.
    ADMIN: sees all cases.
    Others: empty (M61 data isolation applies).
    """
    if actor_role not in ALLOWED_EDD_ROLES:
        return []

    q = db.query(EDDCase)

    if status_filter:
        q = q.filter(EDDCase.status.in_(status_filter))

    if actor_role == "COMPLIANCE_OFFICER" and actor_user_id:
        from sqlalchemy import or_
        q = q.filter(
            or_(
                EDDCase.assigned_to_user_id == actor_user_id,
                EDDCase.status == EDDStatus.OPEN,
            )
        )

    return q.order_by(EDDCase.sla_deadline.asc().nullslast(), EDDCase.created_at.asc()).all()
