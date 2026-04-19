# app/db/models/__init__.py
# All ORM models — M1-M26
# Auth models (M2)
from .auth import Base, Institution, User, UserSession, AgentProfile

# All platform models (M26 — full schema)
from app.db.models_platform import (
    KYCProfile, ConsentRecord, OnboardingOutcome, FallbackCase,
    BOAccount, NotificationLog, AuditLog, Webhook, WebhookDelivery,
    BFIUReport,
)

__all__ = [
    "Base", "Institution", "User", "UserSession", "AgentProfile",
    "KYCProfile", "ConsentRecord", "OnboardingOutcome", "FallbackCase",
    "BOAccount", "NotificationLog", "AuditLog", "Webhook", "WebhookDelivery",
    "BFIUReport",
]
