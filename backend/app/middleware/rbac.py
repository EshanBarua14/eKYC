"""
RBAC Dependencies - M29
Reusable FastAPI dependencies for role-based access control.
"""
from fastapi import HTTPException, Depends
from app.api.v1.routes.auth import get_current_user

def require_role(*allowed_roles: str):
    """
    Dependency factory — allows only specified roles.
    Usage: Depends(require_role("ADMIN", "CHECKER"))
    """
    allowed = {r.upper() for r in allowed_roles}

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        role = (current_user.get("role") or "").upper()
        if role not in allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "error":    "FORBIDDEN",
                    "message":  f"Role {role!r} is not permitted. Required: {sorted(allowed)}",
                    "required": sorted(allowed),
                    "your_role": role,
                }
            )
        return current_user
    return _check

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Shortcut dependency — ADMIN role only."""
    role = (current_user.get("role") or "").upper()
    if role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail={
                "error":    "ADMIN_REQUIRED",
                "message":  "This endpoint requires ADMIN role.",
                "your_role": role,
            }
        )
    return current_user

def require_admin_or_auditor(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow ADMIN or AUDITOR roles."""
    role = (current_user.get("role") or "").upper()
    if role not in ("ADMIN", "AUDITOR"):
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Requires ADMIN or AUDITOR role.", "your_role": role}
        )
    return current_user

def require_checker_or_above(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow ADMIN or CHECKER roles."""
    role = (current_user.get("role") or "").upper()
    if role not in ("ADMIN", "CHECKER"):
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": "Requires CHECKER or ADMIN role.", "your_role": role}
        )
    return current_user
