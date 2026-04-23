"""
Xpert Fintech eKYC Platform
Onboarding Wizard - M4
BFIU Circular No. 29 - Section 3.2
5-step wizard: NID -> PersonalInfo -> Photo -> Signature -> Notification
Server-side state machine with fallback trigger after 3 failed sessions
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Wizard step definitions
# ---------------------------------------------------------------------------
# SIMPLIFIED flow (BFIU Circular No. 29)
STEPS = {
    1: "NID_VERIFICATION",
    2: "BIOMETRIC",
    3: "PERSONAL_INFO",
    4: "PHOTOGRAPH",
    5: "SIGNATURE",
    6: "SCREENING",
    7: "NOTIFICATION",
}
# REGULAR flow adds BENEFICIAL_OWNER before NOTIFICATION
STEPS_REGULAR = {
    1: "NID_VERIFICATION",
    2: "BIOMETRIC",
    3: "PERSONAL_INFO",
    4: "PHOTOGRAPH",
    5: "SIGNATURE",
    6: "SCREENING",
    7: "BENEFICIAL_OWNER",
    8: "NOTIFICATION",
}
STEP_NAMES         = {v: k for k, v in STEPS.items()}
STEP_NAMES_REGULAR = {v: k for k, v in STEPS_REGULAR.items()}

# Signature types allowed per risk level
SIGNATURE_TYPES_LOW_RISK  = ["WET", "ELECTRONIC", "DIGITAL", "PIN"]
SIGNATURE_TYPES_HIGH_RISK = ["WET", "ELECTRONIC", "DIGITAL"]

# Fallback threshold
FALLBACK_SESSION_THRESHOLD = 3   # After 3 failed sessions -> offer face matching

# ---------------------------------------------------------------------------
# In-memory wizard session store (Redis in prod)
# ---------------------------------------------------------------------------
_wizard_sessions: dict = {}

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------
def _append_audit(session: dict, event: str, detail: dict = None):
    """Append audit trail entry (BFIU sec 3.2.3 / 3.3.3)."""
    session.setdefault("audit_trail", []).append({
        "event":     event,
        "detail":    detail or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bfiu_ref":  "BFIU Circular No. 29 - Section 3.2.3",
    })


def create_wizard_session(
    nid_number: str,
    agent_id:   str,
    channel:    str = "AGENCY",
    biometric_mode: str = "FINGERPRINT",
    kyc_type:   str = "SIMPLIFIED",
) -> dict:
    """Create a new onboarding wizard session. kyc_type=SIMPLIFIED|REGULAR"""
    session_id = str(uuid.uuid4())
    now        = datetime.now(timezone.utc).isoformat()
    steps_map  = STEPS_REGULAR if kyc_type.upper() == "REGULAR" else STEPS

    session = {
        "session_id":        session_id,
        "nid_number":        nid_number,
        "agent_id":          agent_id,
        "channel":           channel,
        "biometric_mode":    biometric_mode,
        "kyc_type":          kyc_type.upper(),
        "steps_map":         steps_map,
        "current_step":      1,
        "current_step_name": steps_map[1],
        "status":            "IN_PROGRESS",
        "steps_completed":   [],
        "step_data":         {},
        "audit_trail":       [],
        "failed_sessions":   0,
        "fallback_offered":  False,
        "created_at":        now,
        "updated_at":        now,
    }
    _wizard_sessions[session_id] = session
    _append_audit(session, "SESSION_CREATED", {"kyc_type": kyc_type, "channel": channel})
    return session

def get_wizard_session(session_id: str) -> Optional[dict]:
    """Retrieve wizard session by ID."""
    return _wizard_sessions.get(session_id)

def reset_wizard_sessions():
    """Clear all sessions (for testing)."""
    _wizard_sessions.clear()

# ---------------------------------------------------------------------------
# Step processing
# ---------------------------------------------------------------------------
def process_step(session_id: str, step_data: dict) -> dict:
    """
    Process the current wizard step and advance to next.
    Returns updated session state.
    """
    session = get_wizard_session(session_id)
    if not session:
        return {"success": False, "error": "Session not found"}

    if session["status"] == "COMPLETED":
        return {"success": False, "error": "Session already completed"}

    if session["status"] == "FAILED":
        return {"success": False, "error": "Session failed"}

    steps_map    = session.get("steps_map", STEPS)
    current_step = session["current_step"]
    step_name    = steps_map.get(current_step)

    # Validate step data
    validation = _validate_step(step_name, step_data)
    if not validation["valid"]:
        _append_audit(session, "STEP_FAILED", {"step": step_name, "reason": validation["reason"]})
        return {
            "success":    False,
            "error":      validation["reason"],
            "step":       step_name,
            "session_id": session_id,
        }

    # Store step data
    session["step_data"][step_name] = step_data
    session["steps_completed"].append(step_name)
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    _append_audit(session, "STEP_COMPLETED", {"step": step_name})

    # Advance to next step
    next_step = current_step + 1
    if next_step > len(steps_map):
        session["current_step"]      = current_step
        session["current_step_name"] = step_name
        session["status"]            = "COMPLETED"
        session["completed_at"]      = datetime.now(timezone.utc).isoformat()
        _append_audit(session, "SESSION_COMPLETED", {"steps": session["steps_completed"]})
    else:
        session["current_step"]      = next_step
        session["current_step_name"] = steps_map[next_step]

    return {
        "success":          True,
        "session_id":       session_id,
        "step_completed":   step_name,
        "next_step":        steps_map.get(next_step, "COMPLETED"),
        "next_step_number": next_step if next_step <= len(steps_map) else None,
        "status":           session["status"],
        "steps_completed":  session["steps_completed"],
        "audit_entries":    len(session.get("audit_trail", [])),
    }

def _validate_step(step_name: str, data: dict) -> dict:
    """Validate step-specific required fields."""
    if step_name == "NID_VERIFICATION":
        if not data.get("nid_number"):
            return {"valid": False, "reason": "nid_number required"}
        if not data.get("dob"):
            return {"valid": False, "reason": "dob required"}
        if not data.get("fingerprint_b64") and not data.get("verified"):
            return {"valid": False, "reason": "fingerprint_b64 or verified flag required"}

    elif step_name == "BIOMETRIC":
        if not data.get("biometric_passed"):
            return {"valid": False, "reason": "biometric_passed required (face_match or fingerprint)"}
        if not data.get("biometric_mode"):
            return {"valid": False, "reason": "biometric_mode required (FACE|FINGERPRINT)"}

    elif step_name == "SCREENING":
        if data.get("unscr_hit"):
            return {"valid": False, "reason": "Customer blocked — UNSCR sanctions match"}
        if data.get("pep_blocked"):
            return {"valid": False, "reason": "Customer blocked — PEP/IP screening result"}

    elif step_name == "BENEFICIAL_OWNER":
        if data.get("has_beneficial_owner") is None:
            return {"valid": False, "reason": "has_beneficial_owner (true/false) required"}
        if data.get("has_beneficial_owner") and not data.get("bo_details"):
            return {"valid": False, "reason": "bo_details required when has_beneficial_owner=true"}

    elif step_name == "PERSONAL_INFO":
        if not data.get("full_name"):
            return {"valid": False, "reason": "full_name required"}
        if not data.get("mobile"):
            return {"valid": False, "reason": "mobile required"}

    elif step_name == "PHOTOGRAPH":
        if not data.get("photo_b64") and not data.get("photo_url"):
            return {"valid": False, "reason": "photo_b64 or photo_url required"}

    elif step_name == "SIGNATURE":
        if not data.get("signature_type"):
            return {"valid": False, "reason": "signature_type required"}
        sig_type = data["signature_type"].upper()
        risk     = data.get("risk_grade", "LOW").upper()
        allowed  = SIGNATURE_TYPES_HIGH_RISK if risk == "HIGH" else SIGNATURE_TYPES_LOW_RISK
        if sig_type not in allowed:
            return {
                "valid":  False,
                "reason": f"signature_type {sig_type} not allowed for {risk} risk. Allowed: {allowed}",
            }

    elif step_name == "NOTIFICATION":
        if not data.get("mobile") and not data.get("email"):
            return {"valid": False, "reason": "mobile or email required for notification"}

    return {"valid": True}

# ---------------------------------------------------------------------------
# Fallback trigger
# ---------------------------------------------------------------------------
def record_failed_session(session_id: str) -> dict:
    """
    Record a failed biometric session.
    After FALLBACK_SESSION_THRESHOLD failures, trigger face matching fallback.
    """
    session = get_wizard_session(session_id)
    if not session:
        return {"success": False, "error": "Session not found"}

    session["failed_sessions"] += 1
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    _append_audit(session, "BIOMETRIC_FAILED", {"failed_count": session["failed_sessions"]})

    fallback_required = session["failed_sessions"] >= FALLBACK_SESSION_THRESHOLD

    if fallback_required and not session["fallback_offered"]:
        session["fallback_offered"] = True
        session["status"]           = "FALLBACK_REQUIRED"

    return {
        "session_id":        session_id,
        "failed_sessions":   session["failed_sessions"],
        "fallback_required": fallback_required,
        "fallback_offered":  session["fallback_offered"],
        "threshold":         FALLBACK_SESSION_THRESHOLD,
        "message":           (
            "Fingerprint verification failed 3 times. Face matching offered."
            if fallback_required else
            f"Failed {session['failed_sessions']}/{FALLBACK_SESSION_THRESHOLD} sessions."
        ),
        "bfiu_ref": "BFIU Circular No. 29 - Section 3.2",
    }

# ---------------------------------------------------------------------------
# Notification generator (Step 5)
# ---------------------------------------------------------------------------
def generate_notification(session: dict, success: bool = True) -> dict:
    """
    Generate account opening or failure notification.
    SMS + email dispatched per BFIU sec 3.2 / 3.3 step 5.
    """
    personal   = session.get("step_data", {}).get("PERSONAL_INFO", {})
    nid_data   = session.get("step_data", {}).get("NID_VERIFICATION", {})
    notif_type = "ACCOUNT_OPENING" if success else "EKYC_FAILED"
    notif = {
        "notification_id": str(uuid.uuid4()),
        "session_id":      session["session_id"],
        "type":            notif_type,
        "recipient_name":  personal.get("full_name", "Customer"),
        "mobile":          personal.get("mobile", ""),
        "email":           personal.get("email", ""),
        "nid_number":      nid_data.get("nid_number", ""),
        "channel":         session.get("channel", ""),
        "kyc_type":        session.get("kyc_type", "SIMPLIFIED"),
        "status":          "DISPATCHED",
        "dispatched_at":   datetime.now(timezone.utc).isoformat(),
        "bfiu_ref":        "BFIU Circular No. 29 - Section 3.2 Step 5",
    }
    _append_audit(session, f"NOTIFICATION_{notif_type}", {"notification_id": notif["notification_id"]})
    return notif


def get_audit_trail(session_id: str) -> dict:
    """Retrieve full audit trail for a session (BFIU sec 3.2.3 / 3.3.3)."""
    session = get_wizard_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return {
        "session_id":    session_id,
        "kyc_type":      session.get("kyc_type", "SIMPLIFIED"),
        "status":        session["status"],
        "audit_trail":   session.get("audit_trail", []),
        "total_entries": len(session.get("audit_trail", [])),
        "bfiu_ref":      "BFIU Circular No. 29 - Section 3.2.3 / 3.3.3",
    }
