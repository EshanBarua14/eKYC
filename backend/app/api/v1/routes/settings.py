"""
Platform Settings API — runtime configuration via Admin UI
Overrides .env defaults without server restart
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import json, os

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.core.security import decode_token

_security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_security)) -> dict:
    try:
        return decode_token(creds.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))

router = APIRouter(prefix="/settings", tags=["Settings"])

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "../../../platform_settings.json")

DEFAULT_SETTINGS = {
    # EC / NID API
    "nid_api_mode":        "DEMO",
    "nid_api_base_url":    "https://nid.ec.gov.bd/api/v1",
    "nid_api_key":         "",
    "nid_api_secret":      "",
    # SMS
    "sms_provider":        "ssl_wireless",
    "sms_api_key":         "",
    "sms_api_url":         "https://api.sms.net.bd/send",
    "sms_sender_id":       "XpertKYC",
    # SMTP Email
    "smtp_host":           "smtp.gmail.com",
    "smtp_port":           587,
    "smtp_user":           "",
    "smtp_password":       "",
    "smtp_from":           "noreply@xpertfintech.com.bd",
    # Face matching
    "match_threshold":     45.0,
    "review_threshold":    30.0,
    # BFIU limits
    "bfiu_max_attempts":   10,
    "bfiu_max_sessions":   2,
    # Institution
    "institution_name":    "Xpert Fintech Ltd.",
    "institution_type":    "bank",  # BFIU Circular No. 29 regulated entity
    "institution_code":    "XFL",
    "helpdesk_number":     "+880-2-XXXXXXXX",
    "helpdesk_email":      "support@xpertfintech.com.bd",
    # CORS
    "allowed_origins":     "http://localhost:5173,http://localhost:3000",
    # App
    "app_name":            "Xpert Fintech Ltd. - eKYC Platform",
    "maintenance_mode":    False,
    "demo_mode":           True,
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULT_SETTINGS, **saved}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

class SettingsUpdate(BaseModel):
    key:   str
    value: object

@router.get("")
async def get_settings():
    s = load_settings()
    # Mask secrets for display
    masked = {**s}
    for k in ["nid_api_key","nid_api_secret","smtp_password","sms_api_key"]:
        if masked.get(k):
            masked[k] = "••••••••" + masked[k][-4:] if len(masked[k]) > 4 else "••••••••"
    return {"settings": masked, "has_live_nid": bool(s.get("nid_api_key")), "demo_mode": s.get("demo_mode", True)}

@router.post("")
async def update_settings(updates: dict):
    s = load_settings()
    for k, v in updates.items():
        if k in DEFAULT_SETTINGS:
            s[k] = v
    save_settings(s)
    return {"status": "saved", "settings_count": len(s)}

@router.post("/reset")
async def reset_settings():
    save_settings(DEFAULT_SETTINGS.copy())
    return {"status": "reset"}

@router.get("/status")
async def platform_status():
    s = load_settings()
    return {
        "nid_api_mode":       s.get("nid_api_mode", "DEMO"),
        "has_ec_credentials": bool(s.get("nid_api_key")),
        "has_sms":            bool(s.get("sms_api_key")),
        "has_smtp":           bool(s.get("smtp_user")),
        "demo_mode":          s.get("demo_mode", True),
        "maintenance_mode":   s.get("maintenance_mode", False),
        "institution":        s.get("institution_name", ""),
        "match_threshold":    s.get("match_threshold", 45.0),
        "bfiu_max_attempts":  s.get("bfiu_max_attempts", 10),
        "bfiu_max_sessions":  s.get("bfiu_max_sessions", 2),
    }

# ── UNSCR Manual Pull (Admin only) ───────────────────────────────────────
@router.post("/unscr/pull", tags=["Admin"])
def trigger_unscr_pull(current_user: dict = Depends(get_current_user)):
    """
    Manually trigger UN consolidated list pull.
    Admin only. BFIU §5.1 — list must be current.
    """
    role = current_user.get("role", "")
    if role not in ("ADMIN", "AUDITOR"):
        raise HTTPException(status_code=403, detail="Admin or Auditor role required")
    try:
        from app.services.unscr_service import pull_un_list
        result = pull_un_list(pulled_by=f"manual:{current_user.get('user_id','unknown')}")
        return {
            "triggered_by": current_user.get("user_id"),
            "result": result,
            "bfiu_ref": "BFIU Circular No. 29 §5.1",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/unscr/status", tags=["Admin"])
def unscr_list_status(current_user: dict = Depends(get_current_user)):
    """Get current UNSCR list status — version, entry count, last pull."""
    from app.services.unscr_service import get_list_status
    return get_list_status()
