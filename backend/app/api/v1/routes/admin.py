"""
Admin Console Routes - M13 + M29
ALL endpoints require authentication.
BFIU Circular No. 29 — Production grade.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from app.middleware.rbac import require_admin, require_admin_or_auditor
from app.services.admin_service import (
    create_institution as _db_create_inst,
    list_institutions as _db_list_insts,
    get_institution as _db_get_inst,
    update_institution_status as _db_update_inst_status,
    create_admin_user as _db_create_user,
    list_users as _db_list_users,
    get_user as _db_get_user,
    deactivate_user as _db_deactivate_user,
    update_user_role as _db_update_role,
    get_platform_stats,
)
from app.services.gateway_service import RATE_LIMITS, WHITELISTED_DOMAINS
from app.services.audit_service import list_entries, export_csv, export_json

router = APIRouter(prefix="/admin", tags=["Admin"])

def _now(): return datetime.now(timezone.utc)

# ── In-memory threshold store ────────────────────────────────────────────
_thresholds: dict = {
    "simplified_max_amount":  500_000,
    "regular_min_amount":     500_001,
    "edd_risk_score":         15,
    "high_risk_review_years": 1,
    "med_risk_review_years":  2,
    "low_risk_review_years":  5,
    "max_nid_attempts":       10,
    "max_sessions":           2,
}
_THRESHOLD_DEFAULTS = dict(_thresholds)
_webhooks: dict = {}
_webhook_logs: list = []

# ── Schemas ──────────────────────────────────────────────────────────────
class InstitutionCreateReq(BaseModel):
    name:             str
    short_code:       str
    institution_type: str = "insurance"
    ip_whitelist:     List[str] = []
    schema_name:      Optional[str] = None
    active:           bool = True

class InstitutionUpdateReq(BaseModel):
    name:         Optional[str] = None
    ip_whitelist: List[str] = []
    active:       bool = True
    status:       str = "ACTIVE"

class UserCreateReq(BaseModel):
    username:       Optional[str] = None
    email:          str
    full_name:      Optional[str] = None
    phone:          str = "01700000000"
    role:           str
    institution_id: str
    active:         bool = True
    password:       str = "Admin@12345"

class ThresholdUpdateReq(BaseModel):
    key:   str
    value: float

class WebhookCreateReq(BaseModel):
    url:    str
    events: List[str]
    secret: Optional[str] = None
    active: bool = True

class UserRoleReq(BaseModel):
    role: str

VALID_ROLES = {"ADMIN","CHECKER","MAKER","AGENT","AUDITOR"}

# ══════════════════════════════════════════════════════════════════════════
# 1. Platform Stats
# ══════════════════════════════════════════════════════════════════════════
@router.get("/stats", operation_id="admin_stats")
async def admin_platform_stats(cu: dict = Depends(require_admin)):
    return get_platform_stats()

# ══════════════════════════════════════════════════════════════════════════
# 2. Institution Management
# ══════════════════════════════════════════════════════════════════════════
@router.get("/institutions", operation_id="admin_list_institutions")
async def list_institutions(status: Optional[str] = None, limit: int = Query(50, le=200),
                            cu: dict = Depends(require_admin_or_auditor)):
    items = _db_list_insts(limit=limit)
    return {"institutions": items, "total": len(items)}

@router.post("/institutions", status_code=201, operation_id="admin_create_institution")
async def create_institution(req: InstitutionCreateReq, cu: dict = Depends(require_admin)):
    if req.institution_type not in ("insurance","cmi"):
        raise HTTPException(400, "institution_type must be insurance or cmi")
    result = _db_create_inst(name=req.name, short_code=req.short_code,
                             institution_type=req.institution_type,
                             ip_whitelist=req.ip_whitelist)
    if result.get("error"): raise HTTPException(409, result["error"])
    # patch schema_name if custom provided
    if req.schema_name: result["schema_name"] = req.schema_name
    return {"institution": result}

@router.get("/institutions/{iid}", operation_id="admin_get_institution")
async def get_institution(iid: str, cu: dict = Depends(require_admin_or_auditor)):
    inst = _db_get_inst(iid)
    if not inst: raise HTTPException(404, f"Institution {iid!r} not found")
    return {"institution": inst}

@router.put("/institutions/{iid}", operation_id="admin_update_institution")
async def update_institution(iid: str, req: InstitutionUpdateReq, cu: dict = Depends(require_admin)):
    result = _db_update_inst_status(iid, req.status)
    if result.get("error"): raise HTTPException(404, result["error"])
    if req.name: result["name"] = req.name
    result["active"] = req.active
    return {"institution": result}

@router.delete("/institutions/{iid}", operation_id="admin_delete_institution")
async def delete_institution(iid: str, cu: dict = Depends(require_admin)):
    from app.db.database import db_session
    from app.db.models.auth import Institution
    with db_session() as db:
        r = db.query(Institution).filter_by(id=iid).first()
        if not r: raise HTTPException(404, f"Institution {iid!r} not found")
        db.delete(r)
    return {"deleted": iid}

@router.patch("/institutions/{iid}/status", operation_id="admin_patch_inst_status")
async def patch_institution_status(iid: str, req: InstitutionUpdateReq, cu: dict = Depends(require_admin)):
    result = _db_update_inst_status(iid, req.status)
    if result.get("error"): raise HTTPException(404, result["error"])
    return {"institution": result}

# ══════════════════════════════════════════════════════════════════════════
# 3. User Management
# ══════════════════════════════════════════════════════════════════════════
@router.get("/users", operation_id="admin_list_users")
async def list_users(role: Optional[str] = None, institution_id: Optional[str] = None,
                     limit: int = Query(50, le=200), cu: dict = Depends(require_admin_or_auditor)):
    return {"users": _db_list_users(institution_id, role, limit)}

@router.post("/users", status_code=201, operation_id="admin_create_user")
async def create_user(req: UserCreateReq, cu: dict = Depends(require_admin)):
    if req.role.upper() not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role: {req.role!r}. Must be one of {sorted(VALID_ROLES)}")
    result = _db_create_user(
        email=req.email, full_name=req.full_name or req.username or req.email,
        phone=req.phone, role=req.role, password=req.password,
        institution_id=req.institution_id,
    )
    if result.get("error"): raise HTTPException(409, result["error"])
    # Normalize role to lowercase for backward compat
    result["role"] = result["role"].lower()
    return {"user": result}

@router.get("/users/{uid}", operation_id="admin_get_user")
async def get_user(uid: str, cu: dict = Depends(require_admin_or_auditor)):
    user = _db_get_user(uid)
    if not user: raise HTTPException(404, f"User {uid!r} not found")
    return {"user": user}

@router.put("/users/{uid}/activate", operation_id="admin_activate_user")
async def activate_user(uid: str, active: bool = True, cu: dict = Depends(require_admin)):
    from app.db.database import db_session
    from app.db.models.auth import User
    with db_session() as db:
        r = db.query(User).filter_by(id=uid).first()
        if not r: raise HTTPException(404, f"User {uid!r} not found")
        r.is_active = active
        result = {"id":r.id,"email":r.email,"role":r.role.lower(),
                  "active":active,"is_active":active,
                  "institution_id":r.institution_id}
    return {"user": result}

@router.delete("/users/{uid}", operation_id="admin_delete_user")
async def delete_user(uid: str, cu: dict = Depends(require_admin)):
    from app.db.database import db_session
    from app.db.models.auth import User
    with db_session() as db:
        r = db.query(User).filter_by(id=uid).first()
        if not r: raise HTTPException(404, f"User {uid!r} not found")
        db.delete(r)
    return {"deleted": uid}

@router.patch("/users/{uid}/role", operation_id="admin_update_user_role")
async def update_user_role(uid: str, req: UserRoleReq, cu: dict = Depends(require_admin)):
    if req.role.upper() not in VALID_ROLES:
        raise HTTPException(400, f"role must be one of {sorted(VALID_ROLES)}")
    result = _db_update_role(uid, req.role)
    if result.get("error"): raise HTTPException(404, result["error"])
    return {"user": result}

@router.patch("/users/{uid}/deactivate", operation_id="admin_deactivate_user")
async def deactivate_user_ep(uid: str, cu: dict = Depends(require_admin)):
    result = _db_deactivate_user(uid)
    if result.get("error"): raise HTTPException(404, result["error"])
    return {"user": result, "deactivated": True}

# ══════════════════════════════════════════════════════════════════════════
# 4. Threshold Editor
# ══════════════════════════════════════════════════════════════════════════
@router.get("/thresholds", operation_id="admin_get_thresholds")
async def get_thresholds(cu: dict = Depends(require_admin_or_auditor)):
    return {"thresholds": dict(_thresholds), "bfiu_ref": "BFIU Circular No. 29"}

@router.put("/thresholds", operation_id="admin_update_threshold")
async def update_threshold(req: ThresholdUpdateReq, cu: dict = Depends(require_admin)):
    if req.key not in _thresholds:
        raise HTTPException(400, f"Unknown threshold key: {req.key!r}")
    old = _thresholds[req.key]
    _thresholds[req.key] = req.value
    return {"key": req.key, "old_value": old, "new_value": req.value}

@router.post("/thresholds/reset", operation_id="admin_reset_thresholds")
async def reset_thresholds(cu: dict = Depends(require_admin)):
    _thresholds.update(_THRESHOLD_DEFAULTS)
    return {"thresholds": dict(_thresholds), "reset": True}

# ══════════════════════════════════════════════════════════════════════════
# 5. Webhook Management
# ══════════════════════════════════════════════════════════════════════════
@router.get("/webhooks", operation_id="admin_list_webhooks")
async def list_webhooks(cu: dict = Depends(require_admin_or_auditor)):
    return {"webhooks": list(_webhooks.values()), "total": len(_webhooks)}

@router.post("/webhooks", status_code=201, operation_id="admin_create_webhook")
async def create_webhook(req: WebhookCreateReq, cu: dict = Depends(require_admin)):
    wid = str(uuid.uuid4())
    wh = {"id":wid,"url":req.url,"events":req.events,"active":req.active,
          "created_at":_now().isoformat()}
    _webhooks[wid] = wh
    return {"webhook": wh}

@router.delete("/webhooks/{wid}", operation_id="admin_delete_webhook")
async def delete_webhook(wid: str, cu: dict = Depends(require_admin)):
    if wid not in _webhooks: raise HTTPException(404, f"Webhook {wid!r} not found")
    del _webhooks[wid]
    return {"deleted": wid}

@router.get("/webhooks/logs", operation_id="admin_webhook_logs")
async def webhook_logs(cu: dict = Depends(require_admin_or_auditor)):
    return {"logs": _webhook_logs, "total": len(_webhook_logs)}

# ══════════════════════════════════════════════════════════════════════════
# 6. System Health
# ══════════════════════════════════════════════════════════════════════════
@router.get("/health", operation_id="admin_health")
async def admin_health(cu: dict = Depends(require_admin_or_auditor)):
    from app.db.database import engine
    from sqlalchemy import text
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    from app.core.config import settings
    return {
        "status":    "healthy" if db_ok else "degraded",
        "db":        "ok" if db_ok else "error",
        "db_name":   "ekyc_db (PostgreSQL)" if db_ok else "unavailable",
        "version":   settings.APP_VERSION,
        "timestamp": _now().isoformat(),
        "modules": {
            "auth":"ok","nid":"ok","face_verify":"ok","kyc":"ok",
            "audit":"ok","liveness":"ok","screening":"ok",
        },
        "rate_limits": RATE_LIMITS,
        "whitelisted_domains": list(WHITELISTED_DOMAINS),
        "bfiu_ref": "BFIU Circular No. 29",
    }

# ══════════════════════════════════════════════════════════════════════════
# 7. Audit Logs
# ══════════════════════════════════════════════════════════════════════════
@router.get("/audit-logs", operation_id="admin_audit_logs")
async def admin_audit_logs(
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    cu: dict = Depends(require_admin_or_auditor),
):
    entries = list_entries(event_type=event_type, limit=limit)
    return {"entries": entries, "total": len(entries), "bfiu_ref": "BFIU Circular No. 29"}

@router.get("/audit-logs/export", operation_id="admin_audit_export")
async def admin_audit_export(format: str = "json", cu: dict = Depends(require_admin_or_auditor)):
    if format == "csv":
        data = export_csv()
        return {"data": data, "format": "csv"}
    data = export_json()
    return {"data": data, "format": "json"}
