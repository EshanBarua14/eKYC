"""
M60: EDD Case ORM Models
BFIU Circular No. 29 §4.2, §4.3
Chief AML/CFT Compliance Officer mandatory approval for EDD cases.
Checker role explicitly BLOCKED from EDD approval.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Index,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# BST = UTC+6
BST = timezone(timedelta(hours=6))


def _bst_now() -> datetime:
    return datetime.now(BST)


# ─────────────────────────── EDD States ──────────────────────────────────────
class EDDStatus:
    OPEN = "OPEN"                    # Created, pending CO action
    INFO_REQUESTED = "INFO_REQUESTED"  # CO requested additional info from customer
    UNDER_REVIEW = "UNDER_REVIEW"    # CO actively reviewing
    APPROVED = "APPROVED"            # CO approved — account proceeds
    REJECTED = "REJECTED"            # CO rejected — account rejected/closed
    AUTO_CLOSED = "AUTO_CLOSED"      # 1-month SLA breached, auto-closed per §4.3
    ESCALATED = "ESCALATED"          # Escalated to BFIU (irregular activity)

    ALL = {OPEN, INFO_REQUESTED, UNDER_REVIEW, APPROVED, REJECTED, AUTO_CLOSED, ESCALATED}
    TERMINAL = {APPROVED, REJECTED, AUTO_CLOSED, ESCALATED}
    ACTIVE = {OPEN, INFO_REQUESTED, UNDER_REVIEW}


class EDDTrigger:
    HIGH_RISK_SCORE = "HIGH_RISK_SCORE"      # risk_score >= 15
    PEP_FLAG = "PEP_FLAG"                     # PEP/IP match
    ADVERSE_MEDIA = "ADVERSE_MEDIA"           # adverse media flag
    RISK_REGRADE = "RISK_REGRADE"            # existing customer re-graded high
    IRREGULAR_ACTIVITY = "IRREGULAR_ACTIVITY"  # irregular transaction detected
    MANUAL_TRIGGER = "MANUAL_TRIGGER"        # ADMIN manual escalation


# ─────────────────────────── EDDCase ─────────────────────────────────────────
class EDDCase(Base):
    """
    Enhanced Due Diligence case.
    TABLE: {tenant_schema}.edd_cases

    BFIU §4.2: EDD mandatory for high-risk, PEP/IP-flagged customers.
    BFIU §4.3: Must be assigned to Chief AML/CFT Compliance Officer.
               1-month window before auto-closure for existing customers.
    """
    __tablename__ = "edd_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference number for human display (e.g. EDD-2026-00042)
    case_reference: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )

    # Link to the KYC workflow session that triggered this EDD
    kyc_session_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    # Customer NID (HMAC hash — same pattern as kyc_profiles.nid_hash)
    customer_nid_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )

    # Which event triggered EDD
    trigger: Mapped[str] = mapped_column(
        String(32), nullable=False,
        # CheckConstraint applied via __table_args__
    )

    # Evidence snapshot at time of EDD creation
    trigger_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Risk score at time of creation
    risk_score: Mapped[int] = mapped_column(nullable=False, default=0)

    # Current status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EDDStatus.OPEN, index=True
    )

    # ── Assignment ──────────────────────────────────────────────────────────
    # BFIU §4.3: must be assigned to Chief AML/CFT Compliance Officer
    # assigned_to_user_id references users.id in tenant schema
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # ── SLA Tracking ────────────────────────────────────────────────────────
    # BFIU §4.3: 1-month response window for existing customers
    # For new customers, no fixed window but still tracked
    sla_deadline: Mapped[datetime | None] = mapped_column(
        TIMESTAMPTZ, nullable=True, index=True
    )
    # True if this is an existing customer re-graded (stricter §4.3 applies)
    is_existing_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Decision ────────────────────────────────────────────────────────────
    # Only COMPLIANCE_OFFICER can set these
    decision_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    decision_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps (BST) ────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=_bst_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=_bst_now, onupdate=_bst_now
    )

    # ── Relationships ────────────────────────────────────────────────────────
    actions: Mapped[list["EDDAction"]] = relationship(
        "EDDAction", back_populates="case", order_by="EDDAction.created_at"
    )

    __table_args__ = (
        CheckConstraint(
            f"trigger IN ("
            f"'{EDDTrigger.HIGH_RISK_SCORE}','{EDDTrigger.PEP_FLAG}',"
            f"'{EDDTrigger.ADVERSE_MEDIA}','{EDDTrigger.RISK_REGRADE}',"
            f"'{EDDTrigger.IRREGULAR_ACTIVITY}','{EDDTrigger.MANUAL_TRIGGER}')",
            name="ck_edd_cases_trigger",
        ),
        CheckConstraint(
            f"status IN ("
            f"'{EDDStatus.OPEN}','{EDDStatus.INFO_REQUESTED}',"
            f"'{EDDStatus.UNDER_REVIEW}','{EDDStatus.APPROVED}',"
            f"'{EDDStatus.REJECTED}','{EDDStatus.AUTO_CLOSED}',"
            f"'{EDDStatus.ESCALATED}')",
            name="ck_edd_cases_status",
        ),
        Index("ix_edd_cases_status_deadline", "status", "sla_deadline"),
        Index("ix_edd_cases_assigned", "assigned_to_user_id", "status"),
    )


# ─────────────────────────── EDDAction ───────────────────────────────────────
class EDDAction(Base):
    """
    Append-only audit trail for every EDD case action.
    TABLE: {tenant_schema}.edd_actions

    Immutable — no UPDATE or DELETE permitted (enforced via DB trigger).
    """
    __tablename__ = "edd_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edd_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    action_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    # Who performed the action
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Status transition
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # BST timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=_bst_now
    )

    case: Mapped["EDDCase"] = relationship("EDDCase", back_populates="actions")

    __table_args__ = (
        Index("ix_edd_actions_case_created", "case_id", "created_at"),
    )


# ─────────────────────────── Action Types ────────────────────────────────────
class EDDActionType:
    CASE_CREATED = "CASE_CREATED"
    ASSIGNED = "ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    INFO_REQUESTED = "INFO_REQUESTED"
    INFO_RECEIVED = "INFO_RECEIVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_CLOSED = "AUTO_CLOSED"
    ESCALATED_TO_BFIU = "ESCALATED_TO_BFIU"
    NOTE_ADDED = "NOTE_ADDED"
    SLA_WARNING = "SLA_WARNING"     # 7-day warning before auto-close
