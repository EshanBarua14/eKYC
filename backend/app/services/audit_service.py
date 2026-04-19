"""
Audit Trail Service - M11 + M26
BFIU Circular No. 29 - Section 5.1
PostgreSQL backed via SQLAlchemy
"""
import uuid, csv, io, json as _json
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models import AuditLog

AUDIT_EVENTS = {
    "NID_SCAN_SUBMITTED","NID_SCAN_PASSED","NID_SCAN_REJECTED",
    "SESSION_CREATED","CHALLENGE_ATTEMPTED","CHALLENGE_PASSED",
    "SESSION_LIMIT_REACHED","ATTEMPT_LIMIT_REACHED",
    "FACE_VERIFY_SUBMITTED","FACE_VERIFY_MATCHED","FACE_VERIFY_REVIEW",
    "FACE_VERIFY_FAILED","REVIEW_APPROVED","REVIEW_REJECTED",
    "SESSION_EXPIRED","NID_API_UNAVAILABLE",
    "USER_CREATED","USER_ROLE_CHANGED","USER_DEACTIVATED",
    "AUTH_LOGIN_SUCCESS","AUTH_LOGIN_FAILED","AUTH_LOGOUT",
    "KYC_PROFILE_CREATED","KYC_PROFILE_UPDATED","KYC_UPGRADED",
    "RISK_GRADED","EDD_TRIGGERED","EDD_COMPLETED",
    "SCREENING_PASSED","SCREENING_FLAGGED","SCREENING_BLOCKED",
    "PERIODIC_REVIEW_DUE","PERIODIC_REVIEW_DONE","DECLARATION_SUBMITTED",
    "ACCOUNT_CLOSED","MAKER_ACTION","CHECKER_APPROVED","CHECKER_REJECTED",
}
RETENTION_YEARS = 5

def _now(): return datetime.now(timezone.utc)

def reset_audit_log():
    with db_session() as db:
        db.query(AuditLog).delete()

def log_event(event_type, entity_type, actor_id=None, actor_role=None,
    entity_id=None, session_id=None, ip_address=None,
    before_state=None, after_state=None, metadata=None,
    institution_id=None, bfiu_ref=None):
    if event_type not in AUDIT_EVENTS:
        raise ValueError(f"Unknown event_type: {event_type!r}")
    entry_id = str(uuid.uuid4())
    now = _now()
    retention_until = now.replace(year=now.year + RETENTION_YEARS)
    bfiu_val = bfiu_ref or "BFIU Circular No. 29 - Section 5.1"
    entry = AuditLog(
        id=entry_id, event_type=event_type, entity_type=entity_type,
        entity_id=entity_id, actor_id=actor_id, actor_role=actor_role,
        session_id=session_id, ip_address=ip_address,
        institution_id=institution_id, before_state=before_state,
        after_state=after_state, metadata_=metadata,
        bfiu_ref=bfiu_val, retention_until=retention_until, timestamp=now,
    )
    try:
        with db_session() as db:
            db.add(entry)
    except Exception as e:
        print(f"[AUDIT WARNING] DB write failed: {e}")
    return {
        "id": entry_id, "entry_id": entry_id,
        "event_type": event_type, "entity_type": entity_type,
        "timestamp": now.isoformat(), "retention_until": retention_until.isoformat(),
        "bfiu_ref": bfiu_val, "before_state": before_state,
        "after_state": after_state, "actor_id": actor_id,
        "actor_role": actor_role, "institution_id": institution_id,
    }

def get_entry(entry_id):
    with db_session() as db:
        e = db.query(AuditLog).filter(AuditLog.id == entry_id).first()
        if not e: return None
        return {"id":e.id,"entry_id":e.id,"event_type":e.event_type,
                "entity_type":e.entity_type,"entity_id":e.entity_id,
                "actor_id":e.actor_id,"session_id":e.session_id,
                "timestamp":str(e.timestamp),"bfiu_ref":e.bfiu_ref,
                "institution_id":e.institution_id,"before_state":e.before_state,
                "after_state":e.after_state,
                "retention_until":str(e.retention_until) if e.retention_until else None}

def list_entries(session_id=None, event_type=None, institution_id=None,
                 limit=100, entity_type=None, actor_id=None, **kwargs):
    with db_session() as db:
        q = db.query(AuditLog)
        if session_id:     q = q.filter(AuditLog.session_id == session_id)
        if event_type:     q = q.filter(AuditLog.event_type == event_type)
        if institution_id: q = q.filter(AuditLog.institution_id == institution_id)
        if actor_id:       q = q.filter(AuditLog.actor_id == actor_id)
        rows = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        return [{"id":r.id,"event_type":r.event_type,"entity_type":r.entity_type,
                 "entity_id":r.entity_id,"actor_id":r.actor_id,"session_id":r.session_id,
                 "timestamp":str(r.timestamp),"bfiu_ref":r.bfiu_ref,
                 "institution_id":r.institution_id} for r in rows]

def export_csv(institution_id=None):
    entries = list_entries(institution_id=institution_id, limit=10000)
    buf = io.StringIO()
    if entries:
        w = csv.DictWriter(buf, fieldnames=entries[0].keys())
        w.writeheader(); w.writerows(entries)
    return buf.getvalue()

def export_json(institution_id=None, **kwargs):
    entries = list_entries(institution_id=institution_id, limit=10000)
    return _json.dumps({"bfiu_ref":"BFIU Circular No. 29","entries":entries,
                        "total":len(entries),"export_timestamp":_now().isoformat()})

def get_stats(institution_id=None, **kwargs):
    with db_session() as db:
        q = db.query(AuditLog)
        if institution_id: q = q.filter(AuditLog.institution_id == institution_id)
        total = q.count()
        return {"total_entries":total,"total_events":total,
                "retention_years":RETENTION_YEARS,"bfiu_ref":"BFIU Circular No. 29"}

def get_dashboard_stats(institution_id=None, **kwargs):
    entries = list_entries(institution_id=institution_id, limit=10000)
    ec = {}
    for e in entries:
        et = e.get("event_type","")
        ec[et] = ec.get(et, 0) + 1
    total = len(entries)
    return {"total_events":total,"total_entries":total,"retention_years":RETENTION_YEARS,
            "event_counts":ec,"bfiu_ref":"BFIU Circular No. 29",
            "face_verify_matched": ec.get("FACE_VERIFY_MATCHED",0),
            "face_verify_failed":  ec.get("FACE_VERIFY_FAILED",0),
            "face_verify_review":  ec.get("FACE_VERIFY_REVIEW",0),
            "screening_blocked":   ec.get("SCREENING_BLOCKED",0),
            "edd_triggered":       ec.get("EDD_TRIGGERED",0),
            "auth_login_success":  ec.get("AUTH_LOGIN_SUCCESS",0),
            "auth_login_failed":   ec.get("AUTH_LOGIN_FAILED",0),
            "user_created":        ec.get("USER_CREATED",0)}

def query_log(event_type=None, session_id=None, institution_id=None, actor_id=None, limit=100, **kwargs):
    entries = list_entries(session_id=session_id, event_type=event_type,
                           institution_id=institution_id, actor_id=actor_id, limit=limit)
    return {"entries": entries, "total": len(entries)}

query_log_alias = list_entries
get_log         = list_entries
export_audit    = export_csv
get_audit_stats = get_stats
