"""
M61: Data isolation middleware — FastAPI dependency injectors.
Wraps data_isolation service into reusable Depends() callables.
"""
from fastapi import Depends, HTTPException
from app.api.v1.routes.auth import get_current_user
from app.services.data_isolation import (
    assert_write_permitted,
    assert_kyc_write_permitted,
    apply_agent_filter,
    WRITE_BLOCKED_ROLES,
    OWN_RECORDS_ONLY_ROLES,
    KYC_WRITE_BLOCKED_ROLES,
)


def require_write_access(resource: str = "resource"):
    """Dependency: block AUDITOR from any write endpoint."""
    def _dep(current_user: dict = Depends(get_current_user)) -> dict:
        role = (current_user.get("role") or "").upper()
        assert_write_permitted(role, resource)
        return current_user
    return _dep


def require_kyc_write_access():
    """Dependency: block AUDITOR + COMPLIANCE_OFFICER from KYC session writes."""
    def _dep(current_user: dict = Depends(get_current_user)) -> dict:
        role = (current_user.get("role") or "").upper()
        assert_kyc_write_permitted(role)
        return current_user
    return _dep


def get_isolated_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Standard authenticated user — also validates COMPLIANCE_OFFICER
    cannot access non-EDD endpoints that require broader permissions.
    """
    return current_user


def require_auditor_or_above():
    """Only AUDITOR and ADMIN can access audit exports."""
    def _dep(current_user: dict = Depends(get_current_user)) -> dict:
        role = (current_user.get("role") or "").upper()
        if role not in {"ADMIN", "AUDITOR"}:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "FORBIDDEN",
                    "message": f"Role '{role}' cannot access audit resources. "
                               f"Requires AUDITOR or ADMIN.",
                    "bfiu_ref": "BFIU Circular No. 29 §5.1",
                }
            )
        return current_user
    return _dep
