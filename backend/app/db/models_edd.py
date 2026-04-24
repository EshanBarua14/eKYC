"""
M60: EDD Case ORM Models
BFIU Circular No. 29 §4.2, §4.3
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, TIMESTAMP as TIMESTAMPTZ
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

BST = timezone(timedelta(hours=6))
def _bst_now() -> datetime: return datetime.now(BST)

class EDDStatus:
    OPEN = "OPEN"
    INFO_REQUESTED = "INFO_REQUESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_CLOSED = "AUTO_CLOSED"
    ESCALATED = "ESCALATED"
    ALL = {"OPEN","INFO_REQUESTED","UNDER_REVIEW","APPROVED","REJECTED","AUTO_CLOSED","ESCALATED"}
    TERMINAL = {"APPROVED","REJECTED","AUTO_CLOSED","ESCALATED"}
    ACTIVE = {"OPEN","INFO_REQUESTED","UNDER_REVIEW"}

class EDDTrigger:
    HIGH_RISK_SCORE = "HIGH_RISK_SCORE"
    PEP_FLAG = "PEP_FLAG"
    ADVERSE_MEDIA = "ADVERSE_MEDIA"
    RISK_REGRADE = "RISK_REGRADE"
    IRREGULAR_ACTIVITY = "IRREGULAR_ACTIVITY"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"

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
    SLA_WARNING = "SLA_WARNING"

class EDDCase(Base):
    __tablename__ = "edd_cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    kyc_session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    customer_nid_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    risk_score: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EDDStatus.OPEN, index=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=True, index=True)
    is_existing_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decision_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decision_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now, onupdate=_bst_now)
    actions: Mapped[list["EDDAction"]] = relationship("EDDAction", back_populates="case", order_by="EDDAction.created_at")
    __table_args__ = (
        CheckConstraint("trigger IN ('HIGH_RISK_SCORE','PEP_FLAG','ADVERSE_MEDIA','RISK_REGRADE','IRREGULAR_ACTIVITY','MANUAL_TRIGGER')", name="ck_edd_cases_trigger"),
        CheckConstraint("status IN ('OPEN','INFO_REQUESTED','UNDER_REVIEW','APPROVED','REJECTED','AUTO_CLOSED','ESCALATED')", name="ck_edd_cases_status"),
        Index("ix_edd_cases_status_deadline", "status", "sla_deadline"),
        Index("ix_edd_cases_assigned", "assigned_to_user_id", "status"),
    )

class EDDAction(Base):
    __tablename__ = "edd_actions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edd_cases.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now)
    case: Mapped["EDDCase"] = relationship("EDDCase", back_populates="actions")
    __table_args__ = (Index("ix_edd_actions_case_created", "case_id", "created_at"),)
