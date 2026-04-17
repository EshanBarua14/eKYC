"""
Xpert Fintech eKYC Platform
KYC Lifecycle Management - M10
BFIU Circular No. 29 - Section 5.6, 5.7

Features:
- Periodic review scheduler (HIGH=1yr, MEDIUM=2yr, LOW=5yr)
- Self-declaration workflow (48hr tokenized link)
- Address change verification (2-month SLA)
- Simplified to Regular upgrade
- Account closure with 5-year retention
"""
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Review frequency (BFIU Section 5.7)
# ---------------------------------------------------------------------------
REVIEW_FREQUENCY_YEARS = {"HIGH": 1, "MEDIUM": 2, "LOW": 5}
NOTIFICATION_DAYS_BEFORE = {"HIGH": 30, "MEDIUM": 30, "LOW": 60}
ADDRESS_CHANGE_SLA_DAYS  = 60   # 2 months
DECLARATION_TOKEN_TTL_HOURS = 48

# ---------------------------------------------------------------------------
# In-memory stores (Redis/DB in prod)
# ---------------------------------------------------------------------------
_profiles: dict       = {}   # profile_id -> lifecycle record
_declarations: dict   = {}   # token -> declaration record
_upgrades: dict       = {}   # upgrade_id -> upgrade record
_closures: dict       = {}   # profile_id -> closure record

# ---------------------------------------------------------------------------
# Lifecycle record management
# ---------------------------------------------------------------------------
def register_profile(
    profile_id:    str,
    kyc_type:      str,
    risk_grade:    str,
    full_name:     str,
    mobile:        str,
    email:         Optional[str] = None,
    opened_at:     Optional[str] = None,
) -> dict:
    """Register a KYC profile in the lifecycle manager."""
    now = datetime.now(timezone.utc)
    opened = datetime.fromisoformat(opened_at) if opened_at else now
    review_years = REVIEW_FREQUENCY_YEARS.get(risk_grade.upper(), 2)
    next_review  = opened + timedelta(days=review_years * 365)

    record = {
        "profile_id":   profile_id,
        "kyc_type":     kyc_type,
        "risk_grade":   risk_grade.upper(),
        "full_name":    full_name,
        "mobile":       mobile,
        "email":        email,
        "status":       "ACTIVE",
        "opened_at":    opened.isoformat(),
        "last_review":  opened.isoformat(),
        "next_review":  next_review.isoformat(),
        "review_years": review_years,
        "created_at":   now.isoformat(),
        "updated_at":   now.isoformat(),
        "bfiu_ref":     "BFIU Circular No. 29 - Section 5.7",
    }
    _profiles[profile_id] = record
    return record

def get_profile(profile_id: str) -> Optional[dict]:
    return _profiles.get(profile_id)

def get_all_profiles() -> list:
    return list(_profiles.values())

# ---------------------------------------------------------------------------
# Periodic review scheduler
# ---------------------------------------------------------------------------
def calculate_next_review(risk_grade: str, from_date: Optional[datetime] = None) -> datetime:
    """Calculate next review date based on risk grade."""
    base = from_date or datetime.now(timezone.utc)
    years = REVIEW_FREQUENCY_YEARS.get(risk_grade.upper(), 2)
    return base + timedelta(days=years * 365)

def get_due_reviews(days_ahead: int = 30) -> list:
    """Return profiles whose review is due within days_ahead days."""
    now      = datetime.now(timezone.utc)
    cutoff   = now + timedelta(days=days_ahead)
    due      = []

    for profile in _profiles.values():
        if profile["status"] != "ACTIVE":
            continue
        next_review = datetime.fromisoformat(profile["next_review"])
        if next_review <= cutoff:
            days_until = (next_review - now).days
            due.append({
                **profile,
                "days_until_due":  days_until,
                "overdue":         days_until < 0,
                "notify_days":     NOTIFICATION_DAYS_BEFORE.get(profile["risk_grade"], 30),
            })

    return sorted(due, key=lambda x: x["days_until_due"])

def complete_review(profile_id: str) -> dict:
    """Mark review complete and schedule next review."""
    profile = _profiles.get(profile_id)
    if not profile:
        return {"success": False, "error": "Profile not found"}

    now         = datetime.now(timezone.utc)
    next_review = calculate_next_review(profile["risk_grade"], now)

    profile["last_review"] = now.isoformat()
    profile["next_review"] = next_review.isoformat()
    profile["updated_at"]  = now.isoformat()

    return {
        "success":     True,
        "profile_id":  profile_id,
        "last_review": profile["last_review"],
        "next_review": profile["next_review"],
        "review_years": profile["review_years"],
    }

# ---------------------------------------------------------------------------
# Self-declaration workflow
# ---------------------------------------------------------------------------
def generate_declaration_token(
    profile_id: str,
    mobile:     str,
    email:      Optional[str] = None,
) -> dict:
    """
    Generate a 48-hour tokenized self-declaration link.
    Sent to customer registered mobile + email.
    """
    token   = secrets.token_urlsafe(32)
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(hours=DECLARATION_TOKEN_TTL_HOURS)

    record = {
        "token":      token,
        "profile_id": profile_id,
        "mobile":     mobile,
        "email":      email,
        "status":     "PENDING",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "declared_at": None,
        "declaration_data": None,
    }
    _declarations[token] = record

    return {
        "token":         token,
        "profile_id":    profile_id,
        "expires_at":    expires.isoformat(),
        "ttl_hours":     DECLARATION_TOKEN_TTL_HOURS,
        "dispatch_to":   {"mobile": mobile, "email": email},
        "declaration_url": f"/api/v1/lifecycle/declare/{token}",
        "bfiu_ref":      "BFIU Circular No. 29 - Section 5.7",
    }

def submit_declaration(
    token:          str,
    full_name:      str,
    nid_number:     str,
    contact_number: str,
    ip_address:     Optional[str] = None,
) -> dict:
    """
    Submit self-declaration (no-change scenario).
    Validates token, records declaration, updates review date.
    """
    record = _declarations.get(token)
    if not record:
        return {"success": False, "error": "Invalid token"}

    now = datetime.now(timezone.utc)
    if datetime.fromisoformat(record["expires_at"]) < now:
        return {"success": False, "error": "Token expired"}

    if record["status"] == "COMPLETED":
        return {"success": False, "error": "Declaration already submitted"}

    # Record declaration
    record["status"]     = "COMPLETED"
    record["declared_at"] = now.isoformat()
    record["declaration_data"] = {
        "full_name":      full_name,
        "nid_number":     nid_number,
        "contact_number": contact_number,
        "ip_address":     ip_address,
        "device_fingerprint": None,
    }

    # Update profile review date
    profile_id = record["profile_id"]
    if profile_id in _profiles:
        complete_review(profile_id)

    return {
        "success":     True,
        "token":       token,
        "profile_id":  profile_id,
        "declared_at": record["declared_at"],
        "message":     "Self-declaration recorded. Next review scheduled.",
        "bfiu_ref":    "BFIU Circular No. 29 - Section 5.7",
    }

def get_declaration(token: str) -> Optional[dict]:
    return _declarations.get(token)

# ---------------------------------------------------------------------------
# Simplified to Regular upgrade (BFIU Section 5.6)
# ---------------------------------------------------------------------------
def initiate_upgrade(
    profile_id:     str,
    reason:         str,
    requested_by:   str,
) -> dict:
    """
    Initiate Simplified to Regular eKYC upgrade.
    Requires collection of additional info per BFIU Section 4.
    """
    profile = _profiles.get(profile_id)
    if not profile:
        return {"success": False, "error": "Profile not found"}

    if profile["kyc_type"] != "SIMPLIFIED":
        return {"success": False, "error": "Profile is already REGULAR eKYC"}

    upgrade_id = str(uuid.uuid4())
    now        = datetime.now(timezone.utc)

    upgrade = {
        "upgrade_id":    upgrade_id,
        "profile_id":    profile_id,
        "from_type":     "SIMPLIFIED",
        "to_type":       "REGULAR",
        "reason":        reason,
        "requested_by":  requested_by,
        "status":        "PENDING",
        "additional_info_required": [
            "monthly_income",
            "source_of_funds",
            "tin",
            "account_number",
            "nationality",
        ],
        "created_at":  now.isoformat(),
        "completed_at": None,
        "bfiu_ref":    "BFIU Circular No. 29 - Section 5.6",
    }
    _upgrades[upgrade_id] = upgrade
    return {"success": True, **upgrade}

def complete_upgrade(upgrade_id: str, additional_info: dict) -> dict:
    """Complete the upgrade after additional info is collected."""
    upgrade = _upgrades.get(upgrade_id)
    if not upgrade:
        return {"success": False, "error": "Upgrade not found"}

    if upgrade["status"] == "COMPLETED":
        return {"success": False, "error": "Upgrade already completed"}

    now = datetime.now(timezone.utc)
    upgrade["status"]       = "COMPLETED"
    upgrade["completed_at"] = now.isoformat()
    upgrade["additional_info"] = additional_info

    # Update profile
    profile = _profiles.get(upgrade["profile_id"])
    if profile:
        profile["kyc_type"]   = "REGULAR"
        profile["updated_at"] = now.isoformat()

    return {
        "success":    True,
        "upgrade_id": upgrade_id,
        "profile_id": upgrade["profile_id"],
        "new_type":   "REGULAR",
        "message":    "Profile upgraded to Regular eKYC successfully.",
        "bfiu_ref":   "BFIU Circular No. 29 - Section 5.6",
    }

# ---------------------------------------------------------------------------
# Account closure (5-year retention)
# ---------------------------------------------------------------------------
def close_account(profile_id: str, reason: str) -> dict:
    """
    Close account and start 5-year data retention countdown.
    BFIU Section 5.1: data preserved for 5 years post closure.
    """
    profile = _profiles.get(profile_id)
    if not profile:
        return {"success": False, "error": "Profile not found"}

    now             = datetime.now(timezone.utc)
    retention_until = now + timedelta(days=5 * 365)

    profile["status"]          = "CLOSED"
    profile["closed_at"]        = now.isoformat()
    profile["retention_until"]  = retention_until.isoformat()
    profile["closure_reason"]   = reason
    profile["updated_at"]       = now.isoformat()

    _closures[profile_id] = {
        "profile_id":      profile_id,
        "closed_at":       now.isoformat(),
        "retention_until": retention_until.isoformat(),
        "reason":          reason,
        "retention_years": 5,
        "bfiu_ref":        "BFIU Circular No. 29 - Section 5.1",
    }

    return {
        "success":         True,
        "profile_id":      profile_id,
        "status":          "CLOSED",
        "closed_at":       now.isoformat(),
        "retention_until": retention_until.isoformat(),
        "message":         "Account closed. Data retained for 5 years per BFIU Section 5.1.",
        "bfiu_ref":        "BFIU Circular No. 29 - Section 5.1",
    }

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
def reset_lifecycle():
    """Clear all lifecycle data (for testing)."""
    _profiles.clear()
    _declarations.clear()
    _upgrades.clear()
    _closures.clear()
