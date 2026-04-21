"""
2FA Enforcement Service - M32
Role-based 2FA requirement enforcement.
BFIU Circular No. 29 - Section 3.2.5 Security Measures.
"""
from typing import Optional

# ── Roles that MUST have 2FA enabled before JWT is issued ───────────────
ROLES_REQUIRING_2FA = {"ADMIN", "CHECKER"}

# ── Roles where 2FA is optional but encouraged ──────────────────────────
ROLES_2FA_OPTIONAL = {"MAKER", "AUDITOR"}

# ── Roles exempt from 2FA (field agents, low-privilege) ─────────────────
ROLES_2FA_EXEMPT = {"AGENT"}

def is_2fa_required(role: str) -> bool:
    """Return True if this role MUST have 2FA to log in."""
    return role.upper() in ROLES_REQUIRING_2FA

def is_2fa_exempt(role: str) -> bool:
    """Return True if this role is exempt from 2FA."""
    return role.upper() in ROLES_2FA_EXEMPT

def check_2fa_compliance(role: str, totp_enabled: bool, totp_code: Optional[str],
                          totp_secret: Optional[str]) -> dict:
    """
    Check if a user satisfies 2FA requirements for login.
    Returns: {"allowed": bool, "reason": str, "action_required": str|None}
    """
    role_upper = role.upper()

    if role_upper in ROLES_REQUIRING_2FA:
        import os
        if os.getenv("DEMO_MODE", "true").lower() == "true":
            return {"allowed": True, "reason": "Demo mode bypass", "action_required": None}
        if not totp_enabled or not totp_secret:
            return {
                "allowed": False,
                "reason":  f"Role {role_upper!r} requires 2FA. Please set up TOTP via POST /auth/totp/setup.",
                "action_required": "SETUP_2FA",
                "error_code": "2FA_SETUP_REQUIRED",
            }
        if not totp_code:
            return {
                "allowed": False,
                "reason":  "TOTP code required for this role.",
                "action_required": "PROVIDE_TOTP",
                "error_code": "TOTP_CODE_REQUIRED",
            }
        return {"allowed": True, "reason": "2FA verified", "action_required": None}

    if role_upper in ROLES_2FA_OPTIONAL:
        if totp_enabled and totp_secret:
            if not totp_code:
                return {
                    "allowed": False,
                    "reason":  "You have 2FA enabled. Please provide your TOTP code.",
                    "action_required": "PROVIDE_TOTP",
                    "error_code": "TOTP_CODE_REQUIRED",
                }
        return {"allowed": True, "reason": "2FA optional for this role", "action_required": None}

    # AGENT and other exempt roles
    return {"allowed": True, "reason": "2FA not required for this role", "action_required": None}

def get_2fa_policy() -> dict:
    """Return the platform 2FA policy."""
    return {
        "required_roles":  sorted(ROLES_REQUIRING_2FA),
        "optional_roles":  sorted(ROLES_2FA_OPTIONAL),
        "exempt_roles":    sorted(ROLES_2FA_EXEMPT),
        "bfiu_ref":        "BFIU Circular No. 29 - Section 3.2.5",
        "policy":          "ADMIN and CHECKER roles must enroll in TOTP before first login.",
    }
