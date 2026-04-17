"""
Xpert Fintech eKYC Platform
Maker-Checker Workflow Service - M11
Dual approval for sensitive operations (BFIU compliance requirement)
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

# Sensitive operations requiring dual approval
MAKER_CHECKER_OPERATIONS = {
    "ACCOUNT_CLOSURE",
    "KYC_UPGRADE",
    "RISK_OVERRIDE",
    "USER_ROLE_CHANGE",
    "THRESHOLD_UPDATE",
    "EDD_WAIVER",
    "INSTITUTION_SUSPEND",
}

SLA_HOURS = 24   # Checker must act within 24 hours

# In-memory store
_pending_actions: dict = {}
_completed_actions: dict = {}

def submit_maker_action(
    operation:      str,
    maker_id:       str,
    maker_role:     str,
    entity_id:      str,
    entity_type:    str,
    payload:        dict,
    institution_id: str,
) -> dict:
    """Maker submits an action for checker approval."""
    if operation not in MAKER_CHECKER_OPERATIONS:
        return {"success": False, "error": f"Operation {operation} does not require maker-checker"}

    action_id = str(uuid.uuid4())
    now       = datetime.now(timezone.utc)
    expires   = now + timedelta(hours=SLA_HOURS)

    action = {
        "action_id":      action_id,
        "operation":      operation,
        "maker_id":       maker_id,
        "maker_role":     maker_role,
        "entity_id":      entity_id,
        "entity_type":    entity_type,
        "payload":        payload,
        "institution_id": institution_id,
        "status":         "PENDING",
        "submitted_at":   now.isoformat(),
        "expires_at":     expires.isoformat(),
        "checker_id":     None,
        "checker_note":   None,
        "decided_at":     None,
    }
    _pending_actions[action_id] = action
    return {"success": True, **action}

def checker_decide(
    action_id:   str,
    checker_id:  str,
    checker_role: str,
    decision:    str,
    note:        Optional[str] = None,
) -> dict:
    """Checker approves or rejects a pending maker action."""
    action = _pending_actions.get(action_id)
    if not action:
        return {"success": False, "error": "Action not found"}

    if action["status"] != "PENDING":
        return {"success": False, "error": "Action already decided"}

    if checker_id == action["maker_id"]:
        return {"success": False, "error": "Checker cannot be the same as maker"}

    if decision.upper() not in ["APPROVED", "REJECTED"]:
        return {"success": False, "error": "Decision must be APPROVED or REJECTED"}

    now = datetime.now(timezone.utc)
    if datetime.fromisoformat(action["expires_at"]) < now:
        action["status"] = "EXPIRED"
        return {"success": False, "error": "Action SLA expired"}

    action["status"]      = decision.upper()
    action["checker_id"]  = checker_id
    action["checker_role"] = checker_role
    action["checker_note"] = note
    action["decided_at"]  = now.isoformat()

    _completed_actions[action_id] = action
    del _pending_actions[action_id]

    return {
        "success":    True,
        "action_id":  action_id,
        "status":     action["status"],
        "operation":  action["operation"],
        "decided_at": action["decided_at"],
    }

def get_pending_actions(institution_id: Optional[str] = None) -> list:
    actions = list(_pending_actions.values())
    if institution_id:
        actions = [a for a in actions if a["institution_id"] == institution_id]
    return actions

def get_action(action_id: str) -> Optional[dict]:
    return _pending_actions.get(action_id) or _completed_actions.get(action_id)

def reset_maker_checker():
    _pending_actions.clear()
    _completed_actions.clear()
