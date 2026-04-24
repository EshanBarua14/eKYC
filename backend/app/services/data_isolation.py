"""
M61: Role-based data isolation
BFIU Circular No. 29 — §5.1, §5.2

Rules:
  AGENT             — sees own sessions/profiles only (agent_id filter)
  AUDITOR           — read-only across all records, zero writes
  COMPLIANCE_OFFICER— EDD queue only, blocked from KYC session writes
  CHECKER           — own institution, review queue only
  MAKER             — own institution, no read of other makers' drafts
  ADMIN             — full access
"""
from __future__ import annotations
from typing import Optional
from fastapi import HTTPException

# ── Write-blocked roles ────────────────────────────────────────────────────
WRITE_BLOCKED_ROLES = {"AUDITOR"}

# ── Roles that can only see own records ───────────────────────────────────
OWN_RECORDS_ONLY_ROLES = {"AGENT"}

# ── Roles with no KYC session write access ────────────────────────────────
KYC_WRITE_BLOCKED_ROLES = {"AUDITOR", "COMPLIANCE_OFFICER"}


def assert_write_permitted(role: str, resource: str = "resource") -> None:
    """
    Raise HTTP 403 if role is write-blocked.
    AUDITOR is globally read-only (BFIU §5.1 — audit trail integrity).
    """
    if role.upper() in WRITE_BLOCKED_ROLES:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "WRITE_FORBIDDEN",
                "message": f"Role '{role}' has read-only access. "
                           f"Cannot modify {resource}. BFIU §5.1.",
                "your_role": role,
                "bfiu_ref": "BFIU Circular No. 29 §5.1",
            }
        )


def assert_kyc_write_permitted(role: str) -> None:
    """
    COMPLIANCE_OFFICER and AUDITOR cannot write KYC sessions.
    CO is for EDD only (BFIU §4.3).
    """
    if role.upper() in KYC_WRITE_BLOCKED_ROLES:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "KYC_WRITE_FORBIDDEN",
                "message": f"Role '{role}' cannot initiate or modify KYC sessions. "
                           f"BFIU §4.3 — COMPLIANCE_OFFICER handles EDD only.",
                "your_role": role,
                "bfiu_ref": "BFIU Circular No. 29 §4.3",
            }
        )


def apply_agent_filter(query, model, current_user: dict):
    """
    If caller is AGENT, filter queryset to own records only.
    Other roles see all records within tenant.
    """
    role = (current_user.get("role") or "").upper()
    if role in OWN_RECORDS_ONLY_ROLES:
        user_id = current_user.get("user_id") or current_user.get("sub")
        query = query.filter(model.agent_id == user_id)
    return query


def apply_edd_queue_filter(query, edd_case_model, current_user: dict):
    """
    COMPLIANCE_OFFICER sees own assigned + unassigned OPEN cases.
    ADMIN sees all.
    Others: empty.
    """
    from sqlalchemy import or_
    role = (current_user.get("role") or "").upper()
    user_id = current_user.get("user_id") or current_user.get("sub")

    if role == "COMPLIANCE_OFFICER":
        query = query.filter(
            or_(
                edd_case_model.assigned_to_user_id == user_id,
                edd_case_model.status == "OPEN",
            )
        )
    elif role != "ADMIN":
        # No other role sees EDD queue
        query = query.filter(False)
    return query


def get_readable_resources(role: str) -> list[str]:
    """
    Return list of resource types the role can read.
    Used for audit and documentation.
    """
    role = role.upper()
    base = {
        "ADMIN": ["*"],
        "CHECKER": ["kyc_sessions", "verification_results", "audit_logs", "kyc_profiles"],
        "MAKER": ["kyc_sessions", "kyc_profiles"],
        "AGENT": ["own_kyc_sessions", "own_kyc_profiles"],
        "AUDITOR": ["kyc_sessions", "verification_results", "audit_logs",
                    "kyc_profiles", "edd_cases", "bfiu_reports", "screening_results"],
        "COMPLIANCE_OFFICER": ["edd_cases", "edd_actions"],
    }
    return base.get(role, [])


def get_writable_resources(role: str) -> list[str]:
    """Return list of resource types the role can write."""
    role = role.upper()
    base = {
        "ADMIN": ["*"],
        "CHECKER": ["verification_results:approve", "verification_results:reject"],
        "MAKER": ["kyc_sessions", "kyc_profiles", "nid_scans"],
        "AGENT": ["own_kyc_sessions"],
        "AUDITOR": [],   # READ ONLY
        "COMPLIANCE_OFFICER": ["edd_cases"],
    }
    return base.get(role, [])
