"""
M58 — KYC Workflow Engine
BFIU Circular No. 29 — Full compliant workflow

Simplified KYC:
  data_capture → nid_verification → biometric → screening(UNSCR only) → decision

Regular KYC:
  data_capture → nid_verification → biometric → screening(UNSCR+PEP) → risk_assessment → decision

Decision Logic:
  LOW risk    → APPROVED (auto)
  MEDIUM risk → CONDITIONAL (manual review)
  HIGH risk   → EDD_REQUIRED
  Failed NID  → REJECTED
  Failed bio  → REJECTED (offer fallback after 3 sessions)
"""
import uuid
from datetime import datetime, timezone
from app.core.timezone import bst_isoformat
from typing import Optional

# ── Step definitions ──────────────────────────────────────────────────────
SIMPLIFIED_STEPS = [
    "data_capture",
    "nid_verification",
    "biometric",
    "screening",
    "decision",
]

REGULAR_STEPS = [
    "data_capture",
    "nid_verification",
    "biometric",
    "screening",
    "risk_assessment",
    "decision",
]

# ── Session store (Redis in prod) ─────────────────────────────────────────
_sessions: dict = {}


# ── Public API ────────────────────────────────────────────────────────────
def create_kyc_session(
    kyc_type: str = "SIMPLIFIED",
    agent_id: str = "system",
    channel: str = "AGENCY",
    institution_id: str = "default",
) -> dict:
    """Create a new KYC workflow session."""
    kyc_type = kyc_type.upper()
    if kyc_type not in ("SIMPLIFIED", "REGULAR"):
        kyc_type = "SIMPLIFIED"

    steps = SIMPLIFIED_STEPS if kyc_type == "SIMPLIFIED" else REGULAR_STEPS
    session_id = str(uuid.uuid4())

    session = {
        "session_id":     session_id,
        "kyc_type":       kyc_type,
        "status":         "IN_PROGRESS",
        "current_step":   "data_capture",
        "steps":          steps,
        "completed_steps": [],
        "agent_id":       agent_id,
        "channel":        channel,
        "institution_id": institution_id,
        "data":           {},
        "nid_result":     None,
        "biometric_result": None,
        "screening_result": None,
        "risk_result":    None,
        "decision":       None,
        "audit_trail":    [],
        "created_at":     bst_isoformat(),
        "updated_at":     bst_isoformat(),
        "bfiu_ref":       "BFIU Circular No. 29",
    }
    _append_audit(session, "SESSION_CREATED", {
        "kyc_type": kyc_type,
        "steps": steps,
        "agent_id": agent_id,
    })
    _sessions[session_id] = session
    return session


def get_kyc_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def submit_data_capture(session_id: str, customer_data: dict) -> dict:
    """
    Step 1: Capture basic customer information.
    Required: full_name_en, date_of_birth, mobile_phone, present_address
    Regular also requires: monthly_income, source_of_funds, profession
    """
    session = _get_or_raise(session_id)
    _assert_step(session, "data_capture")

    required = ["full_name_en", "date_of_birth", "mobile_phone", "present_address"]
    if session["kyc_type"] == "REGULAR":
        required += ["monthly_income", "source_of_funds", "profession"]

    missing = [f for f in required if not customer_data.get(f)]
    if missing:
        return _error(session, f"Missing required fields: {', '.join(missing)}", "MISSING_FIELDS")

    session["data"].update(customer_data)
    return _advance_step(session, "data_capture", {"fields_captured": list(customer_data.keys())})


def submit_nid_verification(session_id: str, nid_number: str, ocr_fields: dict = None) -> dict:
    """
    Step 2: Verify NID against EC database (DEMO/LIVE per platform_settings).
    Enforces BFIU 10-attempt / 2-session-per-day limits.
    """
    session = _get_or_raise(session_id)
    _assert_step(session, "nid_verification")

    from app.services.nid_api_client import lookup_nid, cross_match_nid
    from app.services.session_limiter import (
        hash_nid, gate_attempt, increment_attempt_count, increment_session_count,
        check_attempt_limit,
    )

    # BFIU gate check
    gate = gate_attempt(nid_number, session_id)
    if not gate["allowed"]:
        session["status"] = "REJECTED"
        _append_audit(session, "BFIU_LIMIT_REACHED", gate)
        return _error(session, f"BFIU limit: {gate['reason']}", gate["reason"])

    increment_attempt_count(session_id)
    attempt_count = check_attempt_limit(session_id)["current_count"]
    if attempt_count == 1:
        increment_session_count(hash_nid(nid_number))

    # EC lookup
    ec_result = lookup_nid(nid_number)

    if not ec_result["found"]:
        if ec_result.get("status") == "pending_verification":
            session["status"] = "PENDING_VERIFICATION"
            _append_audit(session, "NID_PENDING", ec_result)
            return {
                "session_id": session_id,
                "status": "pending_verification",
                "message": "EC API unavailable — session queued for retry",
                "bfiu_ref": "BFIU Circular No. 29 §3.2",
            }
        session["status"] = "REJECTED"
        _append_audit(session, "NID_NOT_FOUND", {"nid_number": nid_number[-4:]})
        return _error(session, "NID not found in EC database", "NID_NOT_FOUND")

    # Cross-match OCR vs EC
    cross_match = {}
    if ocr_fields:
        cross_match = cross_match_nid(ocr_fields, ec_result["data"])

    nid_result = {
        "verified": True,
        "ec_source": ec_result["source"],
        "ec_data": ec_result["data"],
        "cross_match": cross_match,
        "nid_hash": hash_nid(nid_number),
    }
    session["nid_result"] = nid_result
    session["data"]["nid_number_hash"] = hash_nid(nid_number)
    session["data"]["ec_data"] = ec_result["data"]

    return _advance_step(session, "nid_verification", nid_result)


def submit_biometric(session_id: str, biometric_data: dict) -> dict:
    """
    Step 3: Biometric verification result.
    Accepts face_match or fingerprint result.
    confidence >= threshold → pass; else → fail (offer fallback after 3 sessions).
    """
    session = _get_or_raise(session_id)
    _assert_step(session, "biometric")

    confidence = float(biometric_data.get("confidence", 0))
    passed = biometric_data.get("passed", confidence >= 40)
    method = biometric_data.get("method", "FACE_MATCH")

    bio_result = {
        "passed": passed,
        "confidence": confidence,
        "method": method,
        "liveness_passed": biometric_data.get("liveness_passed", passed),
    }
    session["biometric_result"] = bio_result

    if not passed:
        # Check fallback threshold
        from app.services.onboarding_wizard import FALLBACK_SESSION_THRESHOLD
        failed_count = biometric_data.get("failed_session_count", 1)
        offer_fallback = failed_count >= FALLBACK_SESSION_THRESHOLD

        session["status"] = "REJECTED"
        _append_audit(session, "BIOMETRIC_FAILED", {
            "confidence": confidence,
            "offer_fallback": offer_fallback,
        })
        return {
            "session_id": session_id,
            "status": "REJECTED",
            "step": "biometric",
            "reason": "Biometric verification failed",
            "confidence": confidence,
            "offer_fallback": offer_fallback,
            "fallback_method": "FACE_MATCH" if offer_fallback else None,
            "bfiu_ref": "BFIU Circular No. 29 §3.2",
        }

    return _advance_step(session, "biometric", bio_result)


def submit_screening(session_id: str, name: str = None) -> dict:
    """
    Step 4: Run screening.
    Simplified: UNSCR only.
    Regular: UNSCR + PEP + adverse media.
    MATCH → REJECTED. REVIEW → flag for manual. CLEAR → continue.
    """
    session = _get_or_raise(session_id)
    _assert_step(session, "screening")

    kyc_type = session["kyc_type"]
    screen_name = name or (
        session.get("data", {}).get("ec_data", {}).get("full_name_en")
        or session.get("data", {}).get("full_name_en", "UNKNOWN")
    )

    from app.services.screening_service import run_full_screening
    screening = run_full_screening(screen_name, kyc_type)

    session["screening_result"] = screening

    # Hard block on MATCH
    if screening.get("overall_verdict") == "MATCH":
        session["status"] = "REJECTED"
        _append_audit(session, "SCREENING_BLOCKED", screening)
        return {
            "session_id": session_id,
            "status": "REJECTED",
            "step": "screening",
            "reason": "UNSCR/sanctions match — account opening blocked",
            "screening": screening,
            "bfiu_ref": "BFIU Circular No. 29 §3.2.2",
        }

    # Flag for review but continue
    if screening.get("overall_verdict") == "REVIEW":
        session["data"]["screening_flag"] = True
        _append_audit(session, "SCREENING_REVIEW_FLAG", screening)

    return _advance_step(session, "screening", {"verdict": screening.get("overall_verdict"), "edd_required": screening.get("edd_required", False)})


def submit_risk_assessment(session_id: str, risk_data: dict) -> dict:
    """
    Step 5 (Regular KYC only): Run 7-dimension risk grading.
    Score >= 15 or PEP flag → HIGH → EDD required.
    """
    session = _get_or_raise(session_id)
    _assert_step(session, "risk_assessment")

    if session["kyc_type"] != "REGULAR":
        return _error(session, "risk_assessment step only for REGULAR KYC", "INVALID_STEP")

    from app.services.risk_grading_service import calculate_risk_score
    risk_result = calculate_risk_score(
        onboarding_channel = risk_data.get("onboarding_channel", "AGENCY"),
        residency          = risk_data.get("residency", "RESIDENT"),
        pep_ip_status      = risk_data.get("pep_ip_status", "NONE"),
        product_type       = risk_data.get("product_type", "ORDINARY_LIFE"),
        business_type      = risk_data.get("business_type", "OTHER"),
        profession         = risk_data.get("profession", "OTHER"),
        annual_income_bdt  = float(risk_data.get("monthly_income", 0) or 0) * 12,
        source_of_funds    = risk_data.get("source_of_funds"),
        institution_type   = risk_data.get("institution_type", "INSURANCE"),
        pep_flag           = risk_data.get("pep_ip_status", "NONE") != "NONE",
        adverse_media      = risk_data.get("adverse_media", False),
    )
    session["risk_result"] = risk_result

    return _advance_step(session, "risk_assessment", {
        "score": risk_result.get("total_score"),
        "grade": risk_result.get("risk_grade"),
        "edd_required": risk_result.get("edd_required", False),
    })


def make_decision(session_id: str) -> dict:
    """
    Final step: Apply BFIU decision logic.

    LOW risk    → APPROVED
    MEDIUM risk → CONDITIONAL
    HIGH risk   → EDD_REQUIRED
    Screening MATCH → REJECTED (already blocked in screening step)
    Failed bio/NID  → REJECTED (already set)
    """
    session = _get_or_raise(session_id)
    _assert_step(session, "decision")

    kyc_type = session["kyc_type"]
    screening = session.get("screening_result") or {}
    risk = session.get("risk_result") or {}
    bio = session.get("biometric_result") or {}

    # Determine risk grade
    if kyc_type == "REGULAR":
        grade = risk.get("risk_grade", "MEDIUM")
        score = risk.get("total_score", 0)
        edd_required = risk.get("edd_required", False) or screening.get("edd_required", False)
    else:
        # Simplified: no risk scoring — derive from screening
        grade = "LOW"
        score = 0
        edd_required = screening.get("edd_required", False)
        if screening.get("overall_verdict") == "REVIEW":
            grade = "MEDIUM"

    # Apply decision logic
    if edd_required or grade == "HIGH":
        decision = "EDD_REQUIRED"
        decision_reason = f"High risk / EDD triggered — score={score}, grade={grade}"
    elif grade == "MEDIUM" or screening.get("overall_verdict") == "REVIEW":
        decision = "CONDITIONAL"
        decision_reason = "Medium risk — conditional approval pending manual review"
    else:
        decision = "APPROVED"
        decision_reason = "Low risk — auto approved"

    session["decision"] = {
        "outcome": decision,
        "reason": decision_reason,
        "risk_grade": grade,
        "risk_score": score,
        "edd_required": edd_required,
        "kyc_type": kyc_type,
        "decided_at": bst_isoformat(),
        "bfiu_ref": "BFIU Circular No. 29 §4.2, §6.3",
    }
    session["status"] = decision
    session["current_step"] = "COMPLETE"
    session["completed_steps"].append("decision")
    session["updated_at"] = bst_isoformat()

    _append_audit(session, "DECISION_MADE", session["decision"])
    return {
        "session_id": session_id,
        "decision": decision,
        "reason": decision_reason,
        "risk_grade": grade,
        "risk_score": score,
        "edd_required": edd_required,
        "kyc_type": kyc_type,
        "bfiu_ref": "BFIU Circular No. 29",
    }


def get_session_summary(session_id: str) -> dict:
    """Return full session summary for audit/export."""
    session = _get_or_raise(session_id)
    return {
        "session_id":       session["session_id"],
        "kyc_type":         session["kyc_type"],
        "status":           session["status"],
        "current_step":     session["current_step"],
        "completed_steps":  session["completed_steps"],
        "decision":         session.get("decision"),
        "nid_verified":     bool((session.get("nid_result") or {}).get("verified", False)),
        "biometric_passed": (session.get("biometric_result") or {}).get("passed", False),
        "screening_verdict": (session.get("screening_result") or {}).get("overall_verdict"),
        "risk_grade":       (session.get("risk_result") or {}).get("risk_grade"),
        "created_at":       session["created_at"],
        "updated_at":       session["updated_at"],
        "audit_entries":    len(session.get("audit_trail", [])),
    }


# ── Internal helpers ──────────────────────────────────────────────────────
def _get_or_raise(session_id: str) -> dict:
    s = _sessions.get(session_id)
    if not s:
        raise ValueError(f"Session not found: {session_id}")
    return s


def _assert_step(session: dict, expected_step: str):
    if session["current_step"] != expected_step:
        raise ValueError(
            f"Expected step '{expected_step}', session is at '{session['current_step']}'"
        )


def _advance_step(session: dict, completed: str, detail: dict) -> dict:
    steps = session["steps"]
    session["completed_steps"].append(completed)
    _append_audit(session, f"STEP_COMPLETED:{completed.upper()}", detail)

    idx = steps.index(completed)
    if idx + 1 < len(steps):
        session["current_step"] = steps[idx + 1]
    else:
        session["current_step"] = "COMPLETE"

    session["updated_at"] = bst_isoformat()
    return {
        "session_id":   session["session_id"],
        "step_completed": completed,
        "next_step":    session["current_step"],
        "kyc_type":     session["kyc_type"],
        "status":       session["status"],
        **detail,
    }


def _error(session: dict, message: str, code: str) -> dict:
    session["updated_at"] = bst_isoformat()
    _append_audit(session, f"STEP_ERROR:{code}", {"message": message})
    return {
        "session_id": session["session_id"],
        "error": True,
        "error_code": code,
        "message": message,
        "current_step": session["current_step"],
        "status": session["status"],
    }


def _append_audit(session: dict, event: str, detail: dict = None):
    session.setdefault("audit_trail", []).append({
        "event":     event,
        "detail":    detail or {},
        "timestamp": bst_isoformat(),
        "bfiu_ref":  "BFIU Circular No. 29",
    })


def clear_sessions():
    """Test helper — clear all in-memory sessions."""
    _sessions.clear()
