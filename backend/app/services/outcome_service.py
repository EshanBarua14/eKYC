"""
Onboarding Outcome State Machine - M18
BFIU Circular No. 29 — Section 3.2 & 6.3

Valid state transitions:
  PENDING       -> SCREENING        (background checks started)
  SCREENING     -> RISK_GRADED      (risk score assigned)
  RISK_GRADED   -> APPROVED         (low risk, auto-approved)
  RISK_GRADED   -> PENDING_REVIEW   (high/medium risk, routed to checker)
  RISK_GRADED   -> REJECTED         (sanctions hit / BLOCKED verdict)
  PENDING_REVIEW -> APPROVED        (checker approves)
  PENDING_REVIEW -> REJECTED        (checker rejects)
  ANY            -> FALLBACK_KYC    (EC unavailable, traditional KYC)

Auto-approval criteria (BFIU):
  - verdict == MATCHED
  - risk_grade == LOW
  - screening_result == CLEAR
  - pep_flag == False
  - edd_required == False
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

# ── State definitions ───────────────────────────────────────────────────────
STATES = {
    "PENDING",
    "SCREENING",
    "RISK_GRADED",
    "APPROVED",
    "PENDING_REVIEW",
    "REJECTED",
    "FALLBACK_KYC",
}

# Valid transitions: {from_state: [allowed_to_states]}
TRANSITIONS = {
    "PENDING":        ["SCREENING", "FALLBACK_KYC", "REJECTED"],
    "SCREENING":      ["RISK_GRADED", "REJECTED", "FALLBACK_KYC"],
    "RISK_GRADED":    ["APPROVED", "PENDING_REVIEW", "REJECTED"],
    "PENDING_REVIEW": ["APPROVED", "REJECTED"],
    "APPROVED":       [],
    "REJECTED":       [],
    "FALLBACK_KYC":   ["PENDING"],
}

# ── In-memory outcome store (PostgreSQL in prod) ────────────────────────────
_outcomes: dict = {}   # keyed by session_id

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _outcome_record(session_id: str, state: str, **kwargs) -> dict:
    return {
        "outcome_id":   str(uuid.uuid4())[:8],
        "session_id":   session_id,
        "state":        state,
        "updated_at":   _now(),
        "bfiu_ref":     "BFIU Circular No. 29 — Section 3.2",
        **kwargs,
    }

def create_outcome(
    session_id:       str,
    verdict:          str,
    confidence:       float,
    risk_grade:       str       = "LOW",
    risk_score:       int       = 0,
    pep_flag:         bool      = False,
    edd_required:     bool      = False,
    screening_result: str       = "CLEAR",
    kyc_type:         str       = "SIMPLIFIED",
    full_name:        str       = "N/A",
    agent_id:         str       = "N/A",
    institution_id:   str       = "N/A",
) -> dict:
    """Create initial outcome record in PENDING state."""
    if session_id in _outcomes:
        return {"error": "Outcome already exists", "outcome": _outcomes[session_id]}

    record = _outcome_record(
        session_id, "PENDING",
        verdict=verdict, confidence=confidence,
        risk_grade=risk_grade, risk_score=risk_score,
        pep_flag=pep_flag, edd_required=edd_required,
        screening_result=screening_result, kyc_type=kyc_type,
        full_name=full_name, agent_id=agent_id,
        institution_id=institution_id,
        history=[{"state":"PENDING","timestamp":_now(),"actor":"system","note":"Onboarding initiated"}],
        checker_id=None, checker_note=None, approved_at=None, rejected_at=None,
        fallback_reason=None,
    )
    _outcomes[session_id] = record
    return record


def transition(
    session_id: str,
    to_state:   str,
    actor:      str       = "system",
    note:       Optional[str] = None,
) -> dict:
    """Transition outcome to a new state. Validates allowed transitions."""
    if session_id not in _outcomes:
        return {"success": False, "error": f"No outcome found for session '{session_id}'"}

    record     = _outcomes[session_id]
    from_state = record["state"]

    if to_state not in STATES:
        return {"success": False, "error": f"Unknown state: {to_state}"}

    if to_state not in TRANSITIONS.get(from_state, []):
        return {
            "success": False,
            "error":   f"Invalid transition: {from_state} -> {to_state}",
            "allowed": TRANSITIONS.get(from_state, []),
        }

    record["state"]      = to_state
    record["updated_at"] = _now()
    record["history"].append({
        "state": to_state, "timestamp": _now(),
        "actor": actor, "note": note or "",
    })

    # Set timestamps on terminal states
    if to_state == "APPROVED":
        record["approved_at"] = _now()
    elif to_state == "REJECTED":
        record["rejected_at"] = _now()

    return {"success": True, "outcome": record}


def auto_route(session_id: str) -> dict:
    """
    Run the full auto-routing logic after risk grading.
    LOW risk + CLEAR screening + no PEP + MATCHED -> APPROVED
    Anything else -> PENDING_REVIEW or REJECTED
    """
    if session_id not in _outcomes:
        return {"success": False, "error": "Outcome not found"}

    rec = _outcomes[session_id]

    # First move to SCREENING
    if rec["state"] == "PENDING":
        transition(session_id, "SCREENING", actor="system", note="Background checks started")

    # Then to RISK_GRADED
    if rec["state"] == "SCREENING":
        transition(session_id, "RISK_GRADED", actor="system", note="Risk score assigned")

    # Now decide final routing
    rec = _outcomes[session_id]
    verdict          = rec.get("verdict", "")
    risk_grade       = rec.get("risk_grade", "HIGH")
    pep_flag         = rec.get("pep_flag", False)
    edd_required     = rec.get("edd_required", False)
    screening_result = rec.get("screening_result", "CLEAR")

    # Rejected conditions
    if verdict == "FAILED":
        return transition(session_id, "REJECTED", actor="system", note="Face match FAILED")
    if screening_result == "BLOCKED":
        return transition(session_id, "REJECTED", actor="system", note="Sanctions hit — BLOCKED")

    # Auto-approve: LOW risk, CLEAR, no PEP, MATCHED
    if (verdict == "MATCHED" and risk_grade == "LOW"
            and not pep_flag and not edd_required
            and screening_result == "CLEAR"):
        result = transition(session_id, "APPROVED", actor="system", note="Auto-approved: low risk")
        result["auto_approved"] = True
        return result

    # Everything else -> checker queue
    reason = []
    if risk_grade in ("HIGH", "MEDIUM"): reason.append(f"Risk grade: {risk_grade}")
    if pep_flag:         reason.append("PEP flag")
    if edd_required:     reason.append("EDD required")
    if verdict=="REVIEW":reason.append("Face match: REVIEW")
    if screening_result=="REVIEW": reason.append("Screening: REVIEW")

    result = transition(session_id, "PENDING_REVIEW", actor="system",
                        note=f"Routed to checker: {', '.join(reason)}")
    result["auto_approved"] = False
    result["review_reasons"] = reason
    return result


def checker_decide(
    session_id:  str,
    checker_id:  str,
    decision:    str,   # APPROVE | REJECT
    note:        Optional[str] = None,
) -> dict:
    """Checker approves or rejects a PENDING_REVIEW outcome."""
    if session_id not in _outcomes:
        return {"success": False, "error": "Outcome not found"}

    rec = _outcomes[session_id]
    if rec["state"] != "PENDING_REVIEW":
        return {"success": False, "error": f"Cannot decide — state is {rec['state']}, expected PENDING_REVIEW"}

    if decision.upper() not in ("APPROVE", "REJECT"):
        return {"success": False, "error": "decision must be APPROVE or REJECT"}

    to_state = "APPROVED" if decision.upper() == "APPROVE" else "REJECTED"
    rec["checker_id"]   = checker_id
    rec["checker_note"] = note

    return transition(session_id, to_state, actor=checker_id,
                      note=note or f"Checker {decision.lower()}d")


def trigger_fallback(session_id: str, reason: str = "EC API unavailable") -> dict:
    """Trigger traditional KYC fallback from any state."""
    if session_id not in _outcomes:
        return {"success": False, "error": "Outcome not found"}
    rec = _outcomes[session_id]
    rec["fallback_reason"] = reason
    # Force state regardless of current (emergency fallback)
    rec["state"]      = "FALLBACK_KYC"
    rec["updated_at"] = _now()
    rec["history"].append({"state":"FALLBACK_KYC","timestamp":_now(),
                           "actor":"system","note":reason})
    return {"success": True, "outcome": rec, "fallback_triggered": True}


def get_outcome(session_id: str) -> Optional[dict]:
    return _outcomes.get(session_id)


def list_outcomes(state: Optional[str] = None, limit: int = 100) -> list:
    items = list(_outcomes.values())
    if state:
        items = [o for o in items if o["state"] == state]
    return items[-limit:]


def get_queue_summary() -> dict:
    items = list(_outcomes.values())
    return {s: len([o for o in items if o["state"]==s]) for s in STATES}
