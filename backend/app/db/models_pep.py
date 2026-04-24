"""
M62: PEP/IP Database Models
BFIU Circular No. 29 §4.2

PEP = Politically Exposed Person
IP  = Influential Person (BFIU local category)

Tables:
  pep_entries      — individual PEP/IP records
  pep_list_meta    — last update timestamp, source, version
  pep_audit_log    — append-only log of all add/edit/deactivate actions
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
def _bst_now() -> datetime: return datetime.now(BST)


class PEPCategory:
    PEP = "PEP"          # Politically Exposed Person (international FATF definition)
    IP  = "IP"           # Influential Person (BFIU-specific)
    PEP_FAMILY    = "PEP_FAMILY"     # Family member of PEP
    PEP_ASSOCIATE = "PEP_ASSOCIATE"  # Close associate of PEP
    ALL = {"PEP", "IP", "PEP_FAMILY", "PEP_ASSOCIATE"}


class PEPStatus:
    ACTIVE     = "ACTIVE"
    INACTIVE   = "INACTIVE"   # No longer holds position but record retained
    DECEASED   = "DECEASED"
    ALL = {"ACTIVE", "INACTIVE", "DECEASED"}


class PEPEntry(Base):
    """
    TABLE: pep_entries
    One row per PEP/IP individual.
    BFIU §4.2: PEP/IP screening mandatory for Regular eKYC.
    Score ≥15 OR PEP flag → EDD mandatory.
    """
    __tablename__ = "pep_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # ── Identity ─────────────────────────────────────────────────────────
    full_name_en: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name_bn: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Aliases / alternative names (array stored as JSONB)
    aliases: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    date_of_birth: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    national_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    passport_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nationality: Mapped[str] = mapped_column(String(3), nullable=False, default="BD")  # ISO-3166

    # ── Classification ────────────────────────────────────────────────────
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ministry_or_org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(3), nullable=False, default="BD")

    # ── Risk ──────────────────────────────────────────────────────────────
    # BFIU §4.2: PEP/IP always triggers EDD regardless of risk score
    risk_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="HIGH"
    )
    edd_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Status ────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default=PEPStatus.ACTIVE, index=True
    )

    # ── Source ────────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="MANUAL")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Admin tracking ────────────────────────────────────────────────────
    added_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    last_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Timestamps (BST) ─────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now, onupdate=_bst_now
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('PEP','IP','PEP_FAMILY','PEP_ASSOCIATE')",
            name="ck_pep_entries_category",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','INACTIVE','DECEASED')",
            name="ck_pep_entries_status",
        ),
        CheckConstraint(
            "risk_level IN ('HIGH','MEDIUM','LOW')",
            name="ck_pep_entries_risk_level",
        ),
        Index("ix_pep_entries_name_en", "full_name_en"),
        Index("ix_pep_entries_name_bn", "full_name_bn"),
        Index("ix_pep_entries_category_status", "category", "status"),
        Index("ix_pep_entries_national_id", "national_id"),
    )


class PEPListMeta(Base):
    """
    TABLE: pep_list_meta
    Tracks list version, last update, source.
    """
    __tablename__ = "pep_list_meta"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    list_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_entries: Mapped[int] = mapped_column(nullable=False, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now
    )
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    bfiu_ref: Mapped[str] = mapped_column(
        String(128), nullable=False,
        default="BFIU Circular No. 29 §4.2"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now
    )


class PEPAuditLog(Base):
    """
    TABLE: pep_audit_log
    Append-only. Every add/edit/deactivate logged with BST timestamp.
    BFIU §5.1: immutable audit trail.
    """
    __tablename__ = "pep_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    pep_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=False, default=_bst_now
    )

    __table_args__ = (
        Index("ix_pep_audit_log_entry_id", "pep_entry_id"),
        Index("ix_pep_audit_log_created", "created_at"),
    )


class PEPAuditAction:
    CREATED    = "CREATED"
    UPDATED    = "UPDATED"
    DEACTIVATED = "DEACTIVATED"
    REACTIVATED = "REACTIVATED"
    SEARCHED   = "SEARCHED"
    MATCHED    = "MATCHED"
