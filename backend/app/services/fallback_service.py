"""
Traditional KYC Fallback Service - M19
BFIU Circular No. 29 — Section 3.2

When eKYC fails technically (EC server down, NID not found, 
biometric failure after max attempts), BFIU mandates fallback
to traditional KYC with physical document collection.

Fallback triggers:
  - NID_API_UNAVAILABLE (EC server down)
  - MAX_ATTEMPTS_EXCEEDED (10 NID attempts used)
  - FACE_MATCH_FAILED (repeated biometric failure)
  - MANUAL_TRIGGER (agent decision)

Fallback flow:
  1. Agent creates fallback case
  2. Customer uploads physical documents
  3. Agent reviews documents
  4. Checker approves/rejects
  5. Outcome recorded with FALLBACK_KYC status
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── Document type definitions ───────────────────────────────────────────────
DOCUMENT_TYPES = {
    "NID_FRONT":        "National ID Card — Front",
    "NID_BACK":         "National ID Card — Back",
    "PASSPORT":         "Valid Passport",
    "BIRTH_CERTIFICATE":"Birth Registration Certificate",
    "UTILITY_BILL":     "Utility Bill (address proof)",
    "PHOTO":            "Recent Passport-Size Photograph",
    "SIGNATURE":        "Wet Signature on Form",
    "INCOME_PROOF":     "Income / Source of Funds Proof",
}

REQUIRED_DOCS_SIMPLIFIED = ["NID_FRONT", "NID_BACK", "PHOTO", "SIGNATURE"]
REQUIRED_DOCS_REGULAR    = ["NID_FRONT", "NID_BACK", "PHOTO", "SIGNATURE",
                             "UTILITY_BILL", "INCOME_PROOF"]

TRIGGER_CODES = {
    "NID_API_UNAVAILABLE":    "EC NID server unavailable",
    "MAX_ATTEMPTS_EXCEEDED":  "Maximum NID verification attempts exhausted",
    "FACE_MATCH_FAILED":      "Biometric face match failed repeatedly",
    "FINGERPRINT_FAILED":     "Fingerprint verification failed repeatedly",
    "MANUAL_TRIGGER":         "Agent manually initiated traditional KYC",
    "TECHNICAL_ERROR":        "Technical error during eKYC process",
}

FALLBACK_STATUSES = {
    "INITIATED",
    "DOCS_PENDING",
    "DOCS_SUBMITTED",
    "UNDER_REVIEW",
    "APPROVED",
    "REJECTED",
}

# ── In-memory store ─────────────────────────────────────────────────────────
_fallback_cases: dict = {}   # keyed by case_id
_session_index:  dict = {}   # session_id -> case_id

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_fallback_case(
    session_id:     str,
    trigger_code:   str,
    agent_id:       str       = "N/A",
    institution_id: str       = "N/A",
    kyc_type:       str       = "SIMPLIFIED",
    customer_mobile: Optional[str] = None,
    customer_name:  Optional[str]  = None,
    notes:          Optional[str]  = None,
) -> dict:
    """Create a traditional KYC fallback case."""
    if session_id in _session_index:
        existing = _fallback_cases[_session_index[session_id]]
        return {"case": existing, "already_exists": True}

    if trigger_code not in TRIGGER_CODES:
        trigger_code = "TECHNICAL_ERROR"

    case_id  = f"FKYC-{str(uuid.uuid4())[:8].upper()}"
    required = (REQUIRED_DOCS_REGULAR if kyc_type == "REGULAR"
                else REQUIRED_DOCS_SIMPLIFIED)

    case = {
        "case_id":          case_id,
        "session_id":       session_id,
        "trigger_code":     trigger_code,
        "trigger_reason":   TRIGGER_CODES[trigger_code],
        "agent_id":         agent_id,
        "institution_id":   institution_id,
        "kyc_type":         kyc_type,
        "customer_mobile":  customer_mobile,
        "customer_name":    customer_name,
        "notes":            notes,
        "status":           "INITIATED",
        "required_docs":    required,
        "submitted_docs":   [],
        "missing_docs":     list(required),
        "reviewer_id":      None,
        "reviewer_note":    None,
        "approved_at":      None,
        "rejected_at":      None,
        "created_at":       _now(),
        "updated_at":       _now(),
        "history": [{"status":"INITIATED","timestamp":_now(),
                     "actor":agent_id,"note":TRIGGER_CODES[trigger_code]}],
        "bfiu_ref":         "BFIU Circular No. 29 — Section 3.2",
        "sla_hours":        72,
    }
    _fallback_cases[case_id]          = case
    _session_index[session_id]        = case_id
    return {"case": case, "already_exists": False}


def submit_document(
    case_id:      str,
    doc_type:     str,
    doc_b64:      str,
    filename:     str   = "",
    uploaded_by:  str   = "customer",
) -> dict:
    """Record a submitted document for a fallback case."""
    if case_id not in _fallback_cases:
        return {"success": False, "error": f"Case '{case_id}' not found"}

    if doc_type not in DOCUMENT_TYPES:
        return {"success": False, "error": f"Unknown doc_type. Must be one of: {list(DOCUMENT_TYPES)}"}

    case = _fallback_cases[case_id]
    if case["status"] not in ("INITIATED", "DOCS_PENDING"):
        return {"success": False, "error": f"Cannot submit docs — case status is {case['status']}"}

    # Check for duplicate
    existing = [d for d in case["submitted_docs"] if d["doc_type"] == doc_type]
    if existing:
        existing[0].update({"doc_b64": doc_b64[:50]+"...", "filename": filename,
                            "uploaded_at": _now(), "uploaded_by": uploaded_by})
    else:
        case["submitted_docs"].append({
            "doc_type":    doc_type,
            "doc_label":   DOCUMENT_TYPES[doc_type],
            "filename":    filename,
            "uploaded_by": uploaded_by,
            "uploaded_at": _now(),
            "doc_b64":     doc_b64[:50]+"...",  # truncate for storage
        })

    # Update missing docs
    submitted_types  = {d["doc_type"] for d in case["submitted_docs"]}
    case["missing_docs"] = [d for d in case["required_docs"] if d not in submitted_types]

    # Auto-advance status
    if not case["missing_docs"]:
        case["status"] = "DOCS_SUBMITTED"
        case["history"].append({"status":"DOCS_SUBMITTED","timestamp":_now(),
                                 "actor":uploaded_by,"note":"All required documents submitted"})
    else:
        case["status"] = "DOCS_PENDING"

    case["updated_at"] = _now()
    return {
        "success":      True,
        "case_id":      case_id,
        "doc_type":     doc_type,
        "missing_docs": case["missing_docs"],
        "all_submitted": not case["missing_docs"],
        "status":       case["status"],
    }


def start_review(case_id: str, reviewer_id: str) -> dict:
    """Agent/checker picks up case for review."""
    if case_id not in _fallback_cases:
        return {"success": False, "error": "Case not found"}
    case = _fallback_cases[case_id]
    if case["status"] != "DOCS_SUBMITTED":
        return {"success": False,
                "error": f"Cannot review — status is {case['status']}, expected DOCS_SUBMITTED"}
    case["status"]      = "UNDER_REVIEW"
    case["reviewer_id"] = reviewer_id
    case["updated_at"]  = _now()
    case["history"].append({"status":"UNDER_REVIEW","timestamp":_now(),
                             "actor":reviewer_id,"note":"Review started"})
    return {"success": True, "case": case}


def decide_case(
    case_id:     str,
    reviewer_id: str,
    decision:    str,
    note:        Optional[str] = None,
) -> dict:
    """Approve or reject a traditional KYC case."""
    if case_id not in _fallback_cases:
        return {"success": False, "error": "Case not found"}

    if decision.upper() not in ("APPROVE", "REJECT"):
        return {"success": False, "error": "decision must be APPROVE or REJECT"}

    case = _fallback_cases[case_id]
    if case["status"] != "UNDER_REVIEW":
        return {"success": False,
                "error": f"Cannot decide — status is {case['status']}, expected UNDER_REVIEW"}

    new_status = "APPROVED" if decision.upper() == "APPROVE" else "REJECTED"
    case["status"]        = new_status
    case["reviewer_id"]   = reviewer_id
    case["reviewer_note"] = note
    case["updated_at"]    = _now()
    if new_status == "APPROVED":
        case["approved_at"] = _now()
    else:
        case["rejected_at"] = _now()
    case["history"].append({"status":new_status,"timestamp":_now(),
                             "actor":reviewer_id,"note":note or ""})
    return {"success": True, "case": case}


def get_case(case_id: str) -> Optional[dict]:
    return _fallback_cases.get(case_id)


def get_case_by_session(session_id: str) -> Optional[dict]:
    cid = _session_index.get(session_id)
    return _fallback_cases.get(cid) if cid else None


def list_cases(status: Optional[str] = None, limit: int = 100) -> list:
    items = list(_fallback_cases.values())
    if status:
        items = [c for c in items if c["status"] == status]
    return items[-limit:]


def get_stats() -> dict:
    items = list(_fallback_cases.values())
    return {
        s: len([c for c in items if c["status"] == s])
        for s in FALLBACK_STATUSES
    }
