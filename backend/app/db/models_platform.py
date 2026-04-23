"""
Xpert eKYC Platform — Full ORM Models
BFIU Circular No. 29
All modules: M1-M22 persistent storage
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def _now():
    return datetime.now(timezone.utc)


# ══════════════════════════════════════════════════════════════════════════
# M6 — KYC Profile (already exists, extended)
# ══════════════════════════════════════════════════════════════════════════
class KYCProfile(Base):
    __tablename__ = "kyc_profiles"
    id                       = Column(Integer,      primary_key=True, autoincrement=True)
    session_id               = Column(String(128),  unique=True, index=True, nullable=False)
    verdict                  = Column(String(16),   nullable=False)
    confidence               = Column(Float,        nullable=False)
    institution_type         = Column(String(32),   nullable=False, default="INSURANCE_LIFE")
    institution_id           = Column(String(16),   nullable=True)
    product_type             = Column(String(64),   nullable=True)
    product_amount           = Column(Float,        nullable=True)
    kyc_type                 = Column(String(16),   nullable=False)
    status                   = Column(String(20),   nullable=False, default="PENDING")
    full_name                = Column(String(255),  nullable=False)
    full_name_bn             = Column(String(255),  nullable=True)
    fathers_name             = Column(String(255),  nullable=True)
    mothers_name             = Column(String(255),  nullable=True)
    spouse_name              = Column(String(255),  nullable=True)
    date_of_birth            = Column(String(20),   nullable=False)
    gender                   = Column(String(4),    nullable=True)
    mobile                   = Column(String(20),   nullable=False)
    email                    = Column(String(255),  nullable=True)
    present_address          = Column(Text,         nullable=True)
    permanent_address        = Column(Text,         nullable=True)
    nationality              = Column(String(64),   nullable=False, default="Bangladeshi")
    profession               = Column(String(128),  nullable=True)
    monthly_income           = Column(Float,        nullable=True)
    source_of_funds          = Column(String(255),  nullable=True)
    tin                      = Column(String(32),   nullable=True)
    account_number           = Column(String(64),   nullable=True)
    nominee_name             = Column(String(255),  nullable=True)
    nominee_relation         = Column(String(64),   nullable=True)
    nominee_dob              = Column(String(20),   nullable=True)
    signature_type           = Column(String(20),   nullable=True)
    signature_data           = Column(Text,         nullable=True)
    nid_front_url            = Column(String(512),  nullable=True)
    nid_back_url             = Column(String(512),  nullable=True)
    photo_url                = Column(String(512),  nullable=True)
    pep_flag                 = Column(Boolean,      default=False)
    unscr_checked            = Column(Boolean,      default=False)
    source_of_funds_verified = Column(Boolean,      default=False)
    edd_required             = Column(Boolean,      default=False)
    risk_score               = Column(Integer,      default=0)
    risk_grade               = Column(String(8),    default="LOW")
    agent_id                 = Column(String(64),   nullable=True)
    geolocation              = Column(String(64),   nullable=True)
    bfiu_ref                 = Column(String(64),   default="BFIU Circular No. 29")
    created_at               = Column(DateTime,     default=_now)
    updated_at               = Column(DateTime,     default=_now, onupdate=_now)

    __table_args__ = (
        Index("ix_kyc_status_grade", "status", "risk_grade"),
        Index("ix_kyc_institution", "institution_id"),
    )


# ══════════════════════════════════════════════════════════════════════════
# M16 — Consent Records
# ══════════════════════════════════════════════════════════════════════════
class ConsentRecord(Base):
    __tablename__ = "consent_records"
    consent_id     = Column(String(36),  primary_key=True, index=True)
    session_id     = Column(String(128), unique=True, index=True, nullable=False)
    nid_hash       = Column(String(64),  nullable=True)
    institution_id = Column(String(16),  nullable=True)
    agent_id       = Column(String(64),  nullable=True)
    channel        = Column(String(20),  nullable=False, default="SELF_SERVICE")
    consent_text   = Column(Text,        nullable=True)
    otp_verified   = Column(Boolean,     default=False)
    ip_address     = Column(String(45),  nullable=True)
    user_agent     = Column(Text,        nullable=True)
    status         = Column(String(16),  nullable=False, default="GRANTED")
    revoked_at     = Column(DateTime,    nullable=True)
    bfiu_ref       = Column(String(64),  default="BFIU Circular No. 29 - Section 3.2")
    retention_years= Column(Integer,     default=5)
    timestamp      = Column(DateTime,    default=_now, index=True)


# ══════════════════════════════════════════════════════════════════════════
# M18 — Onboarding Outcomes
# ══════════════════════════════════════════════════════════════════════════
class OnboardingOutcome(Base):
    __tablename__ = "onboarding_outcomes"
    outcome_id     = Column(String(16),  primary_key=True, index=True)
    session_id     = Column(String(128), unique=True, index=True, nullable=False)
    state          = Column(String(20),  nullable=False, default="PENDING", index=True)
    verdict        = Column(String(16),  nullable=False)
    confidence     = Column(Float,       nullable=True)
    risk_grade     = Column(String(8),   nullable=True)
    risk_score     = Column(Integer,     nullable=True)
    pep_flag       = Column(Boolean,     default=False)
    edd_required   = Column(Boolean,     default=False)
    screening_result = Column(String(16), nullable=True)
    kyc_type       = Column(String(16),  nullable=True)
    full_name      = Column(String(255), nullable=True)
    agent_id       = Column(String(64),  nullable=True)
    institution_id = Column(String(16),  nullable=True)
    checker_id     = Column(String(64),  nullable=True)
    checker_note   = Column(Text,        nullable=True)
    auto_approved  = Column(Boolean,     nullable=True)
    fallback_reason= Column(Text,        nullable=True)
    history        = Column(JSON,        default=list)
    approved_at    = Column(DateTime,    nullable=True)
    rejected_at    = Column(DateTime,    nullable=True)
    bfiu_ref       = Column(String(64),  default="BFIU Circular No. 29")
    created_at     = Column(DateTime,    default=_now)
    updated_at     = Column(DateTime,    default=_now, onupdate=_now)


# ══════════════════════════════════════════════════════════════════════════
# M19 — Traditional KYC Fallback
# ══════════════════════════════════════════════════════════════════════════
class FallbackCase(Base):
    __tablename__ = "fallback_cases"
    case_id        = Column(String(20),  primary_key=True, index=True)
    session_id     = Column(String(128), unique=True, index=True, nullable=False)
    trigger_code   = Column(String(40),  nullable=False)
    trigger_reason = Column(Text,        nullable=True)
    agent_id       = Column(String(64),  nullable=True)
    institution_id = Column(String(16),  nullable=True)
    kyc_type       = Column(String(16),  nullable=False, default="SIMPLIFIED")
    customer_mobile= Column(String(20),  nullable=True)
    customer_name  = Column(String(255), nullable=True)
    notes          = Column(Text,        nullable=True)
    status         = Column(String(20),  nullable=False, default="INITIATED", index=True)
    required_docs  = Column(JSON,        default=list)
    submitted_docs = Column(JSON,        default=list)
    missing_docs   = Column(JSON,        default=list)
    reviewer_id    = Column(String(64),  nullable=True)
    reviewer_note  = Column(Text,        nullable=True)
    history        = Column(JSON,        default=list)
    approved_at    = Column(DateTime,    nullable=True)
    rejected_at    = Column(DateTime,    nullable=True)
    sla_hours      = Column(Integer,     default=72)
    bfiu_ref       = Column(String(64),  default="BFIU Circular No. 29")
    created_at     = Column(DateTime,    default=_now)
    updated_at     = Column(DateTime,    default=_now, onupdate=_now)


# ══════════════════════════════════════════════════════════════════════════
# M20 — CMI / BO Accounts
# ══════════════════════════════════════════════════════════════════════════
class BOAccount(Base):
    __tablename__ = "bo_accounts"
    bo_number      = Column(String(20),  primary_key=True, index=True)
    cdbl_ref       = Column(String(20),  unique=True, nullable=True)
    session_id     = Column(String(128), unique=True, index=True, nullable=False)
    full_name      = Column(String(255), nullable=False)
    mobile         = Column(String(20),  nullable=False)
    email          = Column(String(255), nullable=True)
    date_of_birth  = Column(String(20),  nullable=False)
    product_type   = Column(String(30),  nullable=False)
    product_name   = Column(String(100), nullable=True)
    cdbl_code      = Column(String(20),  nullable=True)
    deposit_amount = Column(Float,       nullable=True)
    kyc_type       = Column(String(16),  nullable=False)
    kyc_verdict    = Column(String(16),  nullable=False)
    confidence     = Column(Float,       nullable=True)
    risk_grade     = Column(String(8),   nullable=True)
    risk_score     = Column(Integer,     nullable=True)
    pep_flag       = Column(Boolean,     default=False)
    status         = Column(String(20),  nullable=False, default="PENDING_REVIEW", index=True)
    auto_approved  = Column(Boolean,     default=False)
    institution_id = Column(String(16),  nullable=True)
    agent_id       = Column(String(64),  nullable=True)
    nominee_name   = Column(String(255), nullable=True)
    joint_holder   = Column(String(255), nullable=True)
    threshold_2026 = Column(Boolean,     default=True)
    bfiu_ref       = Column(String(64),  default="BFIU Circular No. 29")
    created_at     = Column(DateTime,    default=_now)
    updated_at     = Column(DateTime,    default=_now, onupdate=_now)


# ══════════════════════════════════════════════════════════════════════════
# M17 — Notification Log
# ══════════════════════════════════════════════════════════════════════════
class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id                = Column(String(16),  primary_key=True, index=True)
    notification_type = Column(String(20),  nullable=False, index=True)
    channel           = Column(String(10),  nullable=False)  # SMS | EMAIL
    recipient         = Column(String(255), nullable=False)
    session_id        = Column(String(128), nullable=False, index=True)
    status            = Column(String(20),  nullable=False)  # SENT | FAILED | DEV_LOGGED
    message_preview   = Column(String(200), nullable=True)
    error             = Column(Text,        nullable=True)
    dev_mode          = Column(Boolean,     default=True)
    timestamp         = Column(DateTime,    default=_now, index=True)


# ══════════════════════════════════════════════════════════════════════════
# M11 — Audit Log (immutable)
# ══════════════════════════════════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id             = Column(String(36),  primary_key=True, index=True)
    event_type     = Column(String(64),  nullable=False, index=True)
    entity_type    = Column(String(64),  nullable=False)
    entity_id      = Column(String(128), nullable=True,  index=True)
    actor_id       = Column(String(128), nullable=True)
    actor_role     = Column(String(20),  nullable=True)
    session_id     = Column(String(128), nullable=True,  index=True)
    ip_address     = Column(String(45),  nullable=True)
    institution_id = Column(String(16),  nullable=True,  index=True)
    before_state   = Column(JSON,        nullable=True)
    after_state    = Column(JSON,        nullable=True)
    metadata_      = Column("metadata", JSON, nullable=True)
    bfiu_ref       = Column(String(64),  nullable=True)
    retention_until= Column(DateTime,    nullable=True)
    timestamp      = Column(DateTime,    default=_now,  index=True)

    __table_args__ = (
        Index("ix_audit_event_time", "event_type", "timestamp"),
        Index("ix_audit_session",    "session_id"),
    )


# ══════════════════════════════════════════════════════════════════════════
# M13 — Webhook Registry
# ══════════════════════════════════════════════════════════════════════════
class Webhook(Base):
    __tablename__ = "webhooks"
    id             = Column(String(16),  primary_key=True, index=True)
    url            = Column(String(512), nullable=False)
    events         = Column(JSON,        default=list)
    secret         = Column(String(255), nullable=True)
    active         = Column(Boolean,     default=True)
    delivery_count = Column(Integer,     default=0)
    last_delivery  = Column(DateTime,    nullable=True)
    created_at     = Column(DateTime,    default=_now)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id           = Column(String(16),  primary_key=True, index=True)
    webhook_id   = Column(String(16),  ForeignKey("webhooks.id"), nullable=True)
    event        = Column(String(64),  nullable=False)
    status       = Column(Integer,     nullable=False)
    duration_ms  = Column(Integer,     nullable=True)
    timestamp    = Column(DateTime,    default=_now, index=True)


# ══════════════════════════════════════════════════════════════════════════
# M21 — BFIU Monthly Reports
# ══════════════════════════════════════════════════════════════════════════
class BFIUReport(Base):
    __tablename__ = "bfiu_reports"
    report_id      = Column(String(30),  primary_key=True, index=True)
    report_type    = Column(String(40),  nullable=False)
    period_year    = Column(Integer,     nullable=False)
    period_month   = Column(Integer,     nullable=False)
    institution_id = Column(String(16),  nullable=True)
    submitted_by   = Column(String(64),  nullable=True)
    report_data    = Column(JSON,        nullable=True)
    generated_at   = Column(DateTime,    default=_now)

    __table_args__ = (Index("ix_bfiu_period", "period_year", "period_month"),)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id             = Column(String(36),  primary_key=True, index=True)
    session_id     = Column(String(128), nullable=False, index=True)
    category       = Column(String(32),  nullable=False, index=True)
    filename       = Column(String(255), nullable=False)
    file_url       = Column(String(512), nullable=False)
    file_path      = Column(String(512), nullable=True)
    file_size      = Column(Integer,     nullable=True)
    sha256         = Column(String(64),  nullable=True)
    mime_type      = Column(String(64),  nullable=True)
    uploaded_by    = Column(String(128), nullable=True)
    institution_id = Column(String(16),  nullable=True)
    bfiu_ref       = Column(String(64),  default="BFIU Circular No. 29")
    created_at     = Column(DateTime,    default=_now, index=True)


# ══════════════════════════════════════════════════════════════════════════
# M37 — UNSCR Consolidated List
# ══════════════════════════════════════════════════════════════════════════
class UNSCREntry(Base):
    __tablename__ = "unscr_entries"

    id              = Column(Integer,     primary_key=True, autoincrement=True)
    un_ref_id       = Column(String(64),  nullable=False, index=True)   # UN reference number
    entry_type      = Column(String(16),  nullable=False, index=True)   # INDIVIDUAL | ENTITY
    primary_name    = Column(String(512), nullable=False)
    aliases         = Column(JSON,        nullable=True)                # list of alias strings
    nationality     = Column(String(64),  nullable=True)
    dob             = Column(String(32),  nullable=True)
    passport_no     = Column(String(64),  nullable=True)
    committee       = Column(String(64),  nullable=True)                # e.g. 1267, 1988, 1718
    listed_on       = Column(String(32),  nullable=True)
    narrative       = Column(Text,        nullable=True)
    search_vector   = Column(Text,        nullable=True)                # FTS: name + aliases joined
    list_version    = Column(String(32),  nullable=False, index=True)   # YYYY-MM-DD pull date
    is_active       = Column(Boolean,     nullable=False, default=True, index=True)
    created_at      = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at      = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_unscr_primary_name", "primary_name"),
        Index("ix_unscr_type_active",  "entry_type", "is_active"),
    )


class UNSCRListMeta(Base):
    """Tracks each UN list pull — version, row count, status."""
    __tablename__ = "unscr_list_meta"

    id              = Column(Integer,     primary_key=True, autoincrement=True)
    list_version    = Column(String(32),  nullable=False, unique=True)
    pull_url        = Column(String(512), nullable=True)
    total_entries   = Column(Integer,     nullable=False, default=0)
    new_entries     = Column(Integer,     nullable=False, default=0)
    removed_entries = Column(Integer,     nullable=False, default=0)
    status          = Column(String(16),  nullable=False, default="SUCCESS")  # SUCCESS | FAILED | PARTIAL
    error_message   = Column(Text,        nullable=True)
    pulled_at       = Column(DateTime(timezone=True), default=_now, nullable=False)
    pulled_by       = Column(String(64),  nullable=False, default="celery_beat")


# ======================================================================
# M38 - Beneficial Ownership (BFIU Circular No. 29 s4.2)
# ======================================================================
class BeneficialOwner(Base):
    __tablename__ = "beneficial_owners"
    id                  = Column(String(36),  primary_key=True, index=True)
    session_id          = Column(String(128), ForeignKey("kyc_profiles.session_id"),
                                 nullable=False, index=True)
    full_name           = Column(String(255), nullable=False)
    nid_number          = Column(String(32),  nullable=True)
    date_of_birth       = Column(String(20),  nullable=True)
    nationality         = Column(String(64),  default="Bangladeshi")
    ownership_type      = Column(String(30),  nullable=False, default="direct")
    ownership_pct       = Column(Float,       nullable=True)
    control_mechanism   = Column(Text,        nullable=True)
    relationship        = Column(String(200), nullable=True)
    source_of_funds     = Column(Text,        nullable=True)
    is_pep              = Column(Boolean,     default=False)
    is_sanctioned       = Column(Boolean,     default=False)
    unscr_checked       = Column(Boolean,     default=False)
    unscr_checked_at    = Column(DateTime,    nullable=True)
    edd_required        = Column(Boolean,     default=False)
    verification_status = Column(String(20),  default="PENDING")
    identified_by       = Column(String(128), nullable=True)
    bfiu_ref            = Column(String(64),  default="BFIU Circular No. 29 s4.2")
    created_at          = Column(DateTime,    default=_now)
    updated_at          = Column(DateTime,    default=_now, onupdate=_now)


class BODeclaration(Base):
    __tablename__ = "bo_declarations"
    id                   = Column(String(36),  primary_key=True, index=True)
    session_id           = Column(String(128), ForeignKey("kyc_profiles.session_id"),
                                  unique=True, nullable=False, index=True)
    has_beneficial_owner = Column(Boolean,     nullable=False)
    declaration_text     = Column(Text,        nullable=True)
    declared_by          = Column(String(128), nullable=True)
    declaration_ip       = Column(String(45),  nullable=True)
    checker_reviewed     = Column(Boolean,     default=False)
    bfiu_ref             = Column(String(64),  default="BFIU Circular No. 29 s4.2")
    created_at           = Column(DateTime,    default=_now)
