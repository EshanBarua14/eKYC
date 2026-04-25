"""
M69: Exit List DB Models
BFIU Circular No. 29 §5.1 — institution internal blacklist

Per-institution exit list persisted in PostgreSQL.
Append-only audit log for all add/deactivate actions.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import Boolean, CheckConstraint, Index, String, Text
from sqlalchemy import TIMESTAMP as TIMESTAMPTZ
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

BST = timezone(timedelta(hours=6))
def _bst_now(): return datetime.now(BST)


class ExitListEntry(Base):
    """TABLE: exit_list_entries — per-institution blacklist."""
    __tablename__ = "exit_list_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_normalised: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    nid_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    additional_info: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    added_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    added_by_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=True)
    deactivated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now, onupdate=_bst_now)

    __table_args__ = (
        Index("ix_exit_list_institution_active", "institution_id", "is_active"),
        Index("ix_exit_list_name_normalised", "name_normalised"),
    )


class ExitListAuditLog(Base):
    """TABLE: exit_list_audit_log — append-only."""
    __tablename__ = "exit_list_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    institution_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now)
