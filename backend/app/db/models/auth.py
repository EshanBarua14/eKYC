"""
Xpert Fintech eKYC Platform
Auth ORM models - Institution, User, Session, AgentProfile
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime,
    ForeignKey, JSON, Integer, Text
)
from sqlalchemy.orm import relationship
from app.db.database import Base

def _now():
    return datetime.now(timezone.utc)

def _uuid():
    return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Institution (public schema - one row per tenant)
# ---------------------------------------------------------------------------
class Institution(Base):
    __tablename__ = "institutions"

    id                       = Column(String(36), primary_key=True, default=_uuid)
    name                     = Column(String(255), nullable=False, unique=True)
    short_code               = Column(String(32),  nullable=False, unique=True)
    institution_type         = Column(String(16),  nullable=False)  # insurance | cmi
    schema_name              = Column(String(64),  nullable=False, unique=True)
    client_id                = Column(String(128), nullable=False, unique=True, index=True)
    client_secret_hash       = Column(String(256), nullable=False)
    ip_whitelist             = Column(JSON,        nullable=True)
    status                   = Column(String(16),  nullable=False, default="ACTIVE", index=True)
    bfiu_threshold_overrides = Column(JSON,        nullable=True)
    created_at               = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at               = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    deactivated_at           = Column(DateTime(timezone=True), nullable=True)

    users  = relationship("User", back_populates="institution", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Institution {self.short_code} ({self.institution_type})>"

# ---------------------------------------------------------------------------
# User (tenant-scoped staff account)
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id                = Column(String(36),  primary_key=True, default=_uuid)
    institution_id    = Column(String(36),  ForeignKey("institutions.id"), nullable=False, index=True)
    email             = Column(String(320), nullable=False, unique=True, index=True)
    phone             = Column(String(20),  nullable=False)
    full_name         = Column(String(255), nullable=False)
    role              = Column(String(32),  nullable=False, index=True)
    password_hash     = Column(String(256), nullable=False)
    totp_secret       = Column(String(64),  nullable=True)
    totp_enabled      = Column(Boolean,     default=False, nullable=False)
    is_active         = Column(Boolean,     default=True,  nullable=False)
    failed_login_count = Column(Integer,    default=0,     nullable=False)
    last_login_at     = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at        = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    institution = relationship("Institution", back_populates="users")
    sessions    = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User {self.email} role={self.role}>"

# ---------------------------------------------------------------------------
# UserSession (active JWT sessions)
# ---------------------------------------------------------------------------
class UserSession(Base):
    __tablename__ = "user_sessions"

    id            = Column(String(36),  primary_key=True, default=_uuid)
    user_id       = Column(String(36),  ForeignKey("users.id"), nullable=False, index=True)
    jti           = Column(String(36),  nullable=False, unique=True, index=True)
    refresh_jti   = Column(String(36),  nullable=True,  unique=True)
    ip_address    = Column(String(45),  nullable=True)
    user_agent    = Column(Text,        nullable=True)
    is_active     = Column(Boolean,     default=True, nullable=False)
    expires_at    = Column(DateTime(timezone=True), nullable=False)
    created_at    = Column(DateTime(timezone=True), default=_now, nullable=False)
    revoked_at    = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession jti={self.jti} active={self.is_active}>"

# ---------------------------------------------------------------------------
# AgentProfile (geo-tagging + assignment metadata)
# ---------------------------------------------------------------------------
class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id             = Column(String(36), primary_key=True, default=_uuid)
    user_id        = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    agent_code     = Column(String(32), nullable=False, unique=True, index=True)
    district       = Column(String(64), nullable=True)
    upazila        = Column(String(64), nullable=True)
    latitude       = Column(String(20), nullable=True)
    longitude      = Column(String(20), nullable=True)
    assigned_zone  = Column(String(64), nullable=True)
    is_active      = Column(Boolean,    default=True, nullable=False)
    created_at     = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at     = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="agent_profile")

    def __repr__(self):
        return f"<AgentProfile {self.agent_code} zone={self.assigned_zone}>"
