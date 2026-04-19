"""
2FA Routes - M32
GET  /auth/2fa/policy        - View 2FA enforcement policy
GET  /auth/2fa/status        - Check current user 2FA status
POST /auth/2fa/enforce       - Admin: enforce 2FA for a user
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.api.v1.routes.auth import get_current_user
from app.middleware.rbac import require_admin
from app.services.twofa_service import (
    get_2fa_policy, is_2fa_required, is_2fa_exempt, ROLES_REQUIRING_2FA,
)

router = APIRouter(prefix="/auth/2fa", tags=["2FA Enforcement"])


class EnforceRequest(BaseModel):
    user_email: str
    enforce:    bool = True


@router.get("/policy", operation_id="twofa_policy")
async def get_policy():
    """View platform 2FA enforcement policy — public endpoint."""
    return get_2fa_policy()


@router.get("/status", operation_id="twofa_status")
async def get_2fa_status(current_user: dict = Depends(get_current_user)):
    """Check 2FA status for the currently logged-in user."""
    role = (current_user.get("role") or "").upper()
    totp_enabled = current_user.get("totp_enabled", False)
    required = is_2fa_required(role)
    exempt   = is_2fa_exempt(role)
    compliant = (not required) or (required and totp_enabled)
    return {
        "role":          role,
        "totp_enabled":  totp_enabled,
        "2fa_required":  required,
        "2fa_exempt":    exempt,
        "compliant":     compliant,
        "message":       "2FA compliant" if compliant else
                         f"Role {role!r} requires 2FA. Set up TOTP via POST /auth/totp/setup.",
        "bfiu_ref":      "BFIU Circular No. 29 - Section 3.2.5",
    }


@router.get("/required-roles", operation_id="twofa_required_roles")
async def get_required_roles():
    """List roles that require 2FA."""
    return {
        "roles_requiring_2fa": sorted(ROLES_REQUIRING_2FA),
        "bfiu_ref": "BFIU Circular No. 29 - Section 3.2.5",
    }
