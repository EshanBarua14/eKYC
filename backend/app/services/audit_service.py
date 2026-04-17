"""
Xpert Fintech eKYC Platform
Audit Trail Service - M11
BFIU Circular No. 29 - Section 5.1
Append-only immutable audit log, 5-year retention, BFIU export
"""
import uuid
import json
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Event type registry (from ORM reference)
# ---------------------------------------------------------------------------
AUDIT_EVENTS = {
    "NID_SCAN_SUBMITTED",   "NID_SCAN_PASSED",      "NID_SCAN_REJECTED",
    "SESSION_CREATED",      "CHALLENGE_ATTEMPTED",  "CHALLENGE_PASSED",
    "SESSION_LIMIT_REACHED","ATTEMPT_LIMIT_REACHED",
    "FACE_VERIFY_SUBMITTED","FACE_VERIFY_MATCHED",  "FACE_VERIFY_REVIEW",
    "FACE_VERIFY_FAILED",   "REVIEW_APPROVED",      "REVIEW_REJECTED",
    "SESSION_EXPIRED",      "NID_API_UNAVAILABLE",
    "USER_CREATED",         "USER_ROLE_CHANGED",    "USER_DEACTIVATED",
    "AUTH_LOGIN_SUCCESS",   "AUTH_LOGIN_FAILED",    "AUTH_LOGOUT",
    "KYC_PROFILE_CREATED",  "KYC_PROFILE_UPDATED",  "KYC_UPGRADED",
    "RISK_GRADED",          "EDD_TRIGGERED",        "EDD_COMPLETED",
    "SCREENING_PASSED",     "SCREENING_FLAGGED",    "SCREENING_BLOCKED",
    "PERIODIC_REVIEW_DUE",  "PERIODIC_REVIEW_DONE", "DECLARATION_SUBMITTED",
    "ACCOUNT_CLOSED",       "MAKER_ACTION",         "CHECKER_APPROVED",
    "CHECKER_REJECTED",
}

RETENTION_YEARS = 5

# ---------------------------------------------------------------------------
# In-memory append-only log (PostgreSQL in prod with RLS + immutability trigger)
# ---------------------------------------------------------------------------
_audit_log: list = []
_log_index: dict = {}   # entry_id -> index in _audit_log

# ---------------------------------------------------------------------------
# Core log function
# ---------------------------------------------------------------------------
def log_event(
    event_type:     str,
    entity_type:    str,
    actor_id:       Optional[str]  = None,
    actor_role:     Optional[str]  = None,
    entity_id:      Optional[str]  = None,
    session_id:     Optional[str]  = None,
    ip_address:     Optional[str]  = None,
    before_state:   Optional[dict] = None,
    after_state:    Optional[dict] = None,
    metadata:       Optional[dict] = None,
    institution_id: Optional[str]  = None,
    bfiu_ref:       Optional[str]  = None,
) -> dict:
    """
    Append an immutable audit log entry.
    Once written, entries cannot be modified or deleted.
    """
    if event_type not in AUDIT_EVENTS:
        raise ValueError(f"Unknown event_type: {event_type}. Must be one of AUDIT_EVENTS.")

    entry_id = str(uuid.uuid4())
    now      = datetime.now(timezone.utc)

    entry = {
        "id":             entry_id,
        "event_type":     event_type,
        "entity_type":    entity_type,
        "actor_id":       actor_id,
        "actor_role":     actor_role,
        "entity_id":      entity_id,
        "session_id":     session_id,
        "ip_address":     ip_address,
        "before_state":   before_state,
        "after_state":    after_state,
        "metadata":       metadata or {},
        "institution_id": institution_id,
        "bfiu_ref":       bfiu_ref or "BFIU Circular No. 29 - Section 5.1",
        "created_at":     now.isoformat(),
        "retention_until": (now + timedelta(days=RETENTION_YEARS * 365)).isoformat(),
    }

    # Append-only: never modify existing entries
    _log_index[entry_id] = len(_audit_log)
    _audit_log.append(entry)
    return entry

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
def get_entry(entry_id: str) -> Optional[dict]:
    idx = _log_index.get(entry_id)
    return _audit_log[idx] if idx is not None else None

def query_log(
    event_type:     Optional[str] = None,
    entity_type:    Optional[str] = None,
    actor_id:       Optional[str] = None,
    institution_id: Optional[str] = None,
    session_id:     Optional[str] = None,
    from_date:      Optional[str] = None,
    to_date:        Optional[str] = None,
    limit:          int = 100,
    offset:         int = 0,
) -> dict:
    """Query audit log with filters."""
    results = _audit_log[:]

    if event_type:
        results = [e for e in results if e["event_type"] == event_type]
    if entity_type:
        results = [e for e in results if e["entity_type"] == entity_type]
    if actor_id:
        results = [e for e in results if e["actor_id"] == actor_id]
    if institution_id:
        results = [e for e in results if e["institution_id"] == institution_id]
    if session_id:
        results = [e for e in results if e["session_id"] == session_id]
    if from_date:
        results = [e for e in results if e["created_at"] >= from_date]
    if to_date:
        results = [e for e in results if e["created_at"] <= to_date]

    total   = len(results)
    results = results[offset:offset + limit]

    return {"total": total, "entries": results, "limit": limit, "offset": offset}

# ---------------------------------------------------------------------------
# BFIU export formats
# ---------------------------------------------------------------------------
def export_json(institution_id: Optional[str] = None) -> str:
    """Export audit log as BFIU-ready JSON."""
    data = query_log(institution_id=institution_id, limit=10000)
    return json.dumps({
        "export_type":     "BFIU_AUDIT_LOG",
        "institution_id":  institution_id,
        "exported_at":     datetime.now(timezone.utc).isoformat(),
        "total_entries":   data["total"],
        "retention_years": RETENTION_YEARS,
        "bfiu_ref":        "BFIU Circular No. 29 - Section 5.1",
        "entries":         data["entries"],
    }, indent=2, default=str)

def export_csv(institution_id: Optional[str] = None) -> str:
    """Export audit log as CSV."""
    data    = query_log(institution_id=institution_id, limit=10000)
    output  = io.StringIO()
    fields  = ["id", "event_type", "entity_type", "actor_id", "actor_role",
                "entity_id", "session_id", "ip_address", "institution_id",
                "bfiu_ref", "created_at", "retention_until"]
    writer  = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data["entries"])
    return output.getvalue()

# ---------------------------------------------------------------------------
# Compliance dashboard stats
# ---------------------------------------------------------------------------
def get_dashboard_stats(institution_id: Optional[str] = None) -> dict:
    """Return compliance dashboard summary stats."""
    all_entries = _audit_log if not institution_id else [
        e for e in _audit_log if e["institution_id"] == institution_id
    ]

    def count(event): return sum(1 for e in all_entries if e["event_type"] == event)

    return {
        "total_events":         len(all_entries),
        "face_verify_matched":  count("FACE_VERIFY_MATCHED"),
        "face_verify_failed":   count("FACE_VERIFY_FAILED"),
        "face_verify_review":   count("FACE_VERIFY_REVIEW"),
        "screening_blocked":    count("SCREENING_BLOCKED"),
        "screening_flagged":    count("SCREENING_FLAGGED"),
        "edd_triggered":        count("EDD_TRIGGERED"),
        "login_failures":       count("AUTH_LOGIN_FAILED"),
        "accounts_closed":      count("ACCOUNT_CLOSED"),
        "periodic_reviews_due": count("PERIODIC_REVIEW_DUE"),
        "checker_approvals":    count("CHECKER_APPROVED"),
        "checker_rejections":   count("CHECKER_REJECTED"),
        "generated_at":         datetime.now(timezone.utc).isoformat(),
        "institution_id":       institution_id,
        "bfiu_ref":             "BFIU Circular No. 29 - Section 5.1",
    }

def reset_audit_log():
    """Clear audit log (for testing only)."""
    _audit_log.clear()
    _log_index.clear()
