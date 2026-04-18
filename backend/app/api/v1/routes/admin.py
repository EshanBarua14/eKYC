"""
Admin Console API — M13
Covers: Institution Mgmt, User Mgmt, Threshold Editor,
        Webhook Mgmt, System Health, Audit Log Viewer
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing   import Optional, List
from datetime import datetime, timezone
import uuid, platform, sys

router = APIRouter(prefix="/admin", tags=["admin"])

# ── in-memory stores (dev) ─────────────────────────────────────────────────
_institutions: dict = {}
_users:        dict = {}
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
_webhooks: dict = {}
_webhook_logs: list = []

# ── schemas ────────────────────────────────────────────────────────────────
class Institution(BaseModel):
    name:         str
    short_code:   str
    ip_whitelist: List[str] = []
    schema_name:  Optional[str] = None
    active:       bool = True

class UserCreate(BaseModel):
    username:    str
    email:       str
    role:        str   # admin|checker|maker|agent|auditor
    institution_id: str
    active:      bool = True

class ThresholdUpdate(BaseModel):
    key:   str
    value: float

class WebhookCreate(BaseModel):
    url:    str
    events: List[str]
    secret: Optional[str] = None
    active: bool = True

# ══════════════════════════════════════════════════════════════════════════
# 1. Institution Management
# ══════════════════════════════════════════════════════════════════════════
@router.get("/institutions")
def list_institutions():
    return {"institutions": list(_institutions.values()), "total": len(_institutions)}

@router.post("/institutions", status_code=201)
def create_institution(body: Institution):
    iid = str(uuid.uuid4())[:8]
    schema = body.schema_name or f"tenant_{body.short_code.lower()}"
    rec = {**body.model_dump(), "id": iid, "schema_name": schema,
           "created_at": datetime.now(timezone.utc).isoformat()}
    _institutions[iid] = rec
    return {"institution": rec}

@router.put("/institutions/{iid}")
def update_institution(iid: str, body: Institution):
    if iid not in _institutions:
        raise HTTPException(404, "Institution not found")
    _institutions[iid].update({**body.model_dump(),
                                "updated_at": datetime.now(timezone.utc).isoformat()})
    return {"institution": _institutions[iid]}

@router.delete("/institutions/{iid}")
def delete_institution(iid: str):
    if iid not in _institutions:
        raise HTTPException(404, "Institution not found")
    del _institutions[iid]
    return {"deleted": iid}

# ══════════════════════════════════════════════════════════════════════════
# 2. User Management
# ══════════════════════════════════════════════════════════════════════════
VALID_ROLES = {"admin", "checker", "maker", "agent", "auditor"}

@router.get("/users")
def list_users(role: Optional[str] = None, institution_id: Optional[str] = None):
    users = list(_users.values())
    if role:
        users = [u for u in users if u["role"] == role]
    if institution_id:
        users = [u for u in users if u["institution_id"] == institution_id]
    return {"users": users, "total": len(users)}

@router.post("/users", status_code=201)
def create_user(body: UserCreate):
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {VALID_ROLES}")
    uid = str(uuid.uuid4())[:8]
    rec = {**body.model_dump(), "id": uid,
           "created_at": datetime.now(timezone.utc).isoformat()}
    _users[uid] = rec
    return {"user": rec}

@router.put("/users/{uid}/activate")
def set_user_active(uid: str, active: bool = True):
    if uid not in _users:
        raise HTTPException(404, "User not found")
    _users[uid]["active"] = active
    _users[uid]["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"user": _users[uid]}

@router.delete("/users/{uid}")
def delete_user(uid: str):
    if uid not in _users:
        raise HTTPException(404, "User not found")
    del _users[uid]
    return {"deleted": uid}

# ══════════════════════════════════════════════════════════════════════════
# 3. Threshold Editor
# ══════════════════════════════════════════════════════════════════════════
@router.get("/thresholds")
def get_thresholds():
    return {"thresholds": _thresholds}

@router.put("/thresholds")
def update_threshold(body: ThresholdUpdate):
    if body.key not in _thresholds:
        raise HTTPException(400, f"Unknown threshold key: {body.key}")
    old = _thresholds[body.key]
    _thresholds[body.key] = body.value
    return {"key": body.key, "old_value": old, "new_value": body.value,
            "updated_at": datetime.now(timezone.utc).isoformat()}

@router.post("/thresholds/reset")
def reset_thresholds():
    _thresholds.update({
        "simplified_max_amount":  500_000,
        "regular_min_amount":     500_001,
        "edd_risk_score":         15,
        "high_risk_review_years": 1,
        "med_risk_review_years":  2,
        "low_risk_review_years":  5,
        "max_nid_attempts":       10,
        "max_sessions":           2,
    })
    return {"reset": True, "thresholds": _thresholds}

# ══════════════════════════════════════════════════════════════════════════
# 4. Webhook Management
# ══════════════════════════════════════════════════════════════════════════
@router.get("/webhooks")
def list_webhooks():
    return {"webhooks": list(_webhooks.values()), "total": len(_webhooks)}

@router.post("/webhooks", status_code=201)
def create_webhook(body: WebhookCreate):
    wid = str(uuid.uuid4())[:8]
    rec = {**body.model_dump(), "id": wid,
           "delivery_count": 0, "last_delivery": None,
           "created_at": datetime.now(timezone.utc).isoformat()}
    _webhooks[wid] = rec
    return {"webhook": rec}

@router.delete("/webhooks/{wid}")
def delete_webhook(wid: str):
    if wid not in _webhooks:
        raise HTTPException(404, "Webhook not found")
    del _webhooks[wid]
    return {"deleted": wid}

@router.get("/webhooks/logs")
def webhook_logs(limit: int = Query(50, le=200)):
    # seed some demo logs if empty
    if not _webhook_logs:
        for i in range(5):
            _webhook_logs.append({
                "id": str(uuid.uuid4())[:8],
                "event": "kyc.onboarding.completed",
                "status": 200 if i % 3 != 0 else 500,
                "duration_ms": 120 + i * 30,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    return {"logs": _webhook_logs[-limit:], "total": len(_webhook_logs)}

# ══════════════════════════════════════════════════════════════════════════
# 5. System Health
# ══════════════════════════════════════════════════════════════════════════
@router.get("/health")
def system_health():
    return {
        "status":      "healthy",
        "version":     "1.0.0-m13",
        "python":      sys.version.split()[0],
        "platform":    platform.system(),
        "uptime_note": "Server restart clears in-memory dev stores",
        "modules": {
            "auth":        "ok", "nid":        "ok",
            "face_verify": "ok", "fingerprint": "ok",
            "risk":        "ok", "screening":   "ok",
            "lifecycle":   "ok", "audit":       "ok",
            "gateway":     "ok", "admin":       "ok",
        },
        "rate_limits": {
            "nid_attempts_per_session": 10,
            "max_concurrent_sessions":  2,
            "api_requests_per_minute":  60,
        },
        "whitelisted_domains": [
            "porichoy.gov.bd", "nid.election.gov.bd",
            "api.xpertfintech.com", "localhost",
        ],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

# ══════════════════════════════════════════════════════════════════════════
# 6. Audit Log Viewer
# ══════════════════════════════════════════════════════════════════════════
_audit_demo = [
    {"id": "a1b2", "event_type": "kyc.onboarding.completed",   "actor": "agent_01", "severity": "info",    "timestamp": "2026-04-18T08:10:00Z"},
    {"id": "c3d4", "event_type": "auth.login.success",          "actor": "admin_01", "severity": "info",    "timestamp": "2026-04-18T08:05:00Z"},
    {"id": "e5f6", "event_type": "risk.edd.triggered",          "actor": "system",   "severity": "warning", "timestamp": "2026-04-18T07:55:00Z"},
    {"id": "g7h8", "event_type": "screening.sanctions.hit",     "actor": "system",   "severity": "critical","timestamp": "2026-04-18T07:40:00Z"},
    {"id": "i9j0", "event_type": "auth.login.failed",           "actor": "unknown",  "severity": "warning", "timestamp": "2026-04-18T07:30:00Z"},
    {"id": "k1l2", "event_type": "kyc.onboarding.nid_fallback", "actor": "agent_02", "severity": "info",    "timestamp": "2026-04-18T07:15:00Z"},
]

@router.get("/audit-logs")
def get_audit_logs(
    event_type: Optional[str] = None,
    severity:   Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    logs = list(_audit_demo)
    if event_type:
        logs = [l for l in logs if event_type.lower() in l["event_type"]]
    if severity:
        logs = [l for l in logs if l["severity"] == severity]
    total = len(logs)
    return {"logs": logs[offset:offset+limit], "total": total, "offset": offset, "limit": limit}

@router.get("/audit-logs/export")
def export_audit_logs(fmt: str = Query("json", pattern="^(json|csv)$")):
    if fmt == "csv":
        lines = ["id,event_type,actor,severity,timestamp"]
        for l in _audit_demo:
            lines.append(f"{l['id']},{l['event_type']},{l['actor']},{l['severity']},{l['timestamp']}")
        return {"format": "csv", "data": "\n".join(lines)}
    return {"format": "json", "data": _audit_demo}
