"""
Institution Onboarding Service - M33
Full lifecycle: Application -> Review -> Approval -> Activation
BFIU Circular No. 29 - Section 2 (Institutional Requirements)
"""
import uuid
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models.auth import Institution

ONBOARDING_STATES = [
    "APPLIED", "UNDER_REVIEW", "APPROVED", "REJECTED",
    "ACTIVE", "SUSPENDED", "DEACTIVATED"
]

INSTITUTION_TYPES = ["insurance", "cmi"]

def _now(): return datetime.now(timezone.utc)
def _nows(): return _now().isoformat()

# ── In-memory application store (pre-DB stage) ───────────────────────────
_applications: dict = {}

def _app_dict(a: dict) -> dict:
    return {k: v for k, v in a.items()}

# ── Application stage ────────────────────────────────────────────────────
def submit_application(
    name: str, short_code: str, institution_type: str,
    contact_email: str, contact_phone: str,
    address: str, license_number: str,
    submitted_by: str = "applicant",
    ip_whitelist: list = None,
) -> dict:
    """Submit a new institution onboarding application."""
    if institution_type not in INSTITUTION_TYPES:
        return {"error": f"institution_type must be one of {INSTITUTION_TYPES}"}
    short_code = short_code.upper()
    # Check duplicate
    for app in _applications.values():
        if app["short_code"] == short_code:
            return {"error": f"Short code {short_code!r} already exists"}
    app_id = f"APP-{str(uuid.uuid4())[:8].upper()}"
    application = {
        "app_id":          app_id,
        "name":            name,
        "short_code":      short_code,
        "institution_type": institution_type,
        "contact_email":   contact_email,
        "contact_phone":   contact_phone,
        "address":         address,
        "license_number":  license_number,
        "ip_whitelist":    ip_whitelist or [],
        "status":          "APPLIED",
        "submitted_by":    submitted_by,
        "submitted_at":    _nows(),
        "reviewed_by":     None,
        "reviewed_at":     None,
        "approved_by":     None,
        "approved_at":     None,
        "rejection_reason": None,
        "notes":           [],
        "bfiu_ref":        "BFIU Circular No. 29 - Section 2",
    }
    _applications[app_id] = application
    return {"application": application, "app_id": app_id}

def get_application(app_id: str) -> Optional[dict]:
    a = _applications.get(app_id)
    return _app_dict(a) if a else None

def list_applications(status: str = None) -> list:
    apps = list(_applications.values())
    if status:
        apps = [a for a in apps if a["status"] == status]
    return [_app_dict(a) for a in apps]

# ── Review stage ─────────────────────────────────────────────────────────
def start_review(app_id: str, reviewer_id: str, note: str = "") -> dict:
    """Admin starts reviewing an application."""
    app = _applications.get(app_id)
    if not app: return {"error": f"Application {app_id!r} not found"}
    if app["status"] != "APPLIED":
        return {"error": f"Cannot review — status is {app['status']!r}"}
    app["status"]      = "UNDER_REVIEW"
    app["reviewed_by"] = reviewer_id
    app["reviewed_at"] = _nows()
    if note: app["notes"].append({"by": reviewer_id, "note": note, "at": _nows()})
    return {"application": _app_dict(app), "success": True}

def add_review_note(app_id: str, reviewer_id: str, note: str) -> dict:
    """Add a note to an application during review."""
    app = _applications.get(app_id)
    if not app: return {"error": f"Application {app_id!r} not found"}
    app["notes"].append({"by": reviewer_id, "note": note, "at": _nows()})
    return {"application": _app_dict(app), "success": True}

# ── Approval stage ───────────────────────────────────────────────────────
def approve_application(app_id: str, approved_by: str) -> dict:
    """
    Approve application and create Institution record with client credentials.
    """
    app = _applications.get(app_id)
    if not app: return {"error": f"Application {app_id!r} not found"}
    if app["status"] not in ("APPLIED", "UNDER_REVIEW"):
        return {"error": f"Cannot approve — status is {app['status']!r}"}

    # Generate client credentials
    client_id     = f"client_{app['short_code'].lower()}_{str(uuid.uuid4())[:8]}"
    client_secret = secrets.token_urlsafe(32)
    secret_hash   = hashlib.sha256(client_secret.encode()).hexdigest()
    schema_name   = f"tenant_{app['short_code'].lower()}"

    # Create Institution in DB
    with db_session() as db:
        existing = db.query(Institution).filter_by(short_code=app["short_code"]).first()
        if existing:
            # Reuse existing institution (idempotent approval)
            institution_id = existing.id
            existing.status = "ACTIVE"; existing.updated_at = _now()
            app["status"] = "APPROVED"
            app["approved_by"] = approved_by
            app["approved_at"] = _nows()
            app["institution_id"] = institution_id
            app["client_id"] = existing.client_id
            app["schema_name"] = existing.schema_name
            return {
                "application": _app_dict(app),
                "institution_id": institution_id,
                "client_id": existing.client_id,
                "client_secret": "already_issued",
                "schema_name": existing.schema_name,
                "success": True,
                "bfiu_ref": "BFIU Circular No. 29 - Section 2",
            }
        inst = Institution(
            id=str(uuid.uuid4()), name=app["name"],
            short_code=app["short_code"],
            institution_type=app["institution_type"],
            schema_name=schema_name,
            client_id=client_id,
            client_secret_hash=secret_hash,
            ip_whitelist=app.get("ip_whitelist", []),
            status="ACTIVE",
            created_at=_now(), updated_at=_now(),
        )
        db.add(inst); db.flush()
        institution_id = inst.id

    app["status"]      = "APPROVED"
    app["approved_by"] = approved_by
    app["approved_at"] = _nows()
    app["institution_id"] = institution_id
    app["client_id"]   = client_id
    app["schema_name"] = schema_name

    return {
        "application":    _app_dict(app),
        "institution_id": institution_id,
        "client_id":      client_id,
        "client_secret":  client_secret,  # shown ONCE — store securely
        "schema_name":    schema_name,
        "success":        True,
        "bfiu_ref":       "BFIU Circular No. 29 - Section 2",
    }

def reject_application(app_id: str, rejected_by: str, reason: str) -> dict:
    """Reject an application with a reason."""
    app = _applications.get(app_id)
    if not app: return {"error": f"Application {app_id!r} not found"}
    if app["status"] not in ("APPLIED", "UNDER_REVIEW"):
        return {"error": f"Cannot reject — status is {app['status']!r}"}
    app["status"]           = "REJECTED"
    app["rejection_reason"] = reason
    app["notes"].append({"by": rejected_by, "note": f"Rejected: {reason}", "at": _nows()})
    return {"application": _app_dict(app), "success": True}

# ── Activation ───────────────────────────────────────────────────────────
def activate_institution(institution_id: str) -> dict:
    """Activate an approved institution."""
    with db_session() as db:
        inst = db.query(Institution).filter_by(id=institution_id).first()
        if not inst: return {"error": "Institution not found"}
        inst.status = "ACTIVE"; inst.updated_at = _now()
        return {"institution_id": institution_id, "status": "ACTIVE", "success": True}

def suspend_institution(institution_id: str, reason: str = "") -> dict:
    """Suspend an active institution."""
    with db_session() as db:
        inst = db.query(Institution).filter_by(id=institution_id).first()
        if not inst: return {"error": "Institution not found"}
        inst.status = "SUSPENDED"; inst.updated_at = _now()
        return {"institution_id": institution_id, "status": "SUSPENDED",
                "reason": reason, "success": True}

def get_onboarding_stats() -> dict:
    """Return onboarding pipeline statistics."""
    apps = list(_applications.values())
    counts = {s: len([a for a in apps if a["status"] == s]) for s in ONBOARDING_STATES}
    with db_session() as db:
        from app.db.models.auth import Institution
        active_institutions = db.query(Institution).filter_by(status="ACTIVE").count()
    return {
        "pipeline":            counts,
        "total_applications":  len(apps),
        "active_institutions": active_institutions,
        "bfiu_ref":            "BFIU Circular No. 29 - Section 2",
    }

def reset_applications():
    """Reset for testing."""
    _applications.clear()
