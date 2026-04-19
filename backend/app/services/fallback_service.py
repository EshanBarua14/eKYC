"""Fallback Service - M19 + M26 PostgreSQL backed"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models import FallbackCase

TRIGGER_CODES = {
    "EC_API_TIMEOUT","EC_API_DOWN","EC_API_AUTH_FAILED",
    "NID_API_UNAVAILABLE","NID_API_TIMEOUT","NID_API_ERROR",
    "FINGERPRINT_DEVICE_ERROR","FACE_MATCH_EXHAUSTED",
    "LIVENESS_EXHAUSTED","IMAGE_QUALITY_FAILED","NID_FORMAT_INVALID",
    "MANUAL_TRIGGER",
}
VALID_DOC_TYPES = {"NID_FRONT","NID_BACK","PHOTO","SIGNATURE","UTILITY_BILL","INCOME_PROOF","ADDRESS_PROOF"}
REQUIRED_DOCS_SIMPLIFIED = ["NID_FRONT","NID_BACK","PHOTO","SIGNATURE"]
REQUIRED_DOCS_REGULAR    = ["NID_FRONT","NID_BACK","PHOTO","SIGNATURE","UTILITY_BILL","INCOME_PROOF"]
DOCUMENT_TYPES = ["NID_FRONT","NID_BACK","PHOTO","SIGNATURE","UTILITY_BILL","INCOME_PROOF","ADDRESS_PROOF"]

def _now(): return datetime.now(timezone.utc)
def _nows(): return _now().isoformat()

def _row(r) -> dict:
    return {"case_id":r.case_id,"session_id":r.session_id,"trigger_code":r.trigger_code,
            "trigger_reason":r.trigger_reason,"status":r.status,"agent_id":r.agent_id,
            "institution_id":r.institution_id,"kyc_type":r.kyc_type,
            "customer_name":r.customer_name,"customer_mobile":r.customer_mobile,
            "required_docs":r.required_docs or [],"submitted_docs":r.submitted_docs or [],
            "missing_docs":r.missing_docs or [],"notes":r.notes,
            "reviewer_id":r.reviewer_id,"reviewer_note":r.reviewer_note,
            "history":r.history or [],"sla_hours":r.sla_hours,
            "approved_at":str(r.approved_at) if r.approved_at else None,
            "created_at":str(r.created_at),"bfiu_ref":r.bfiu_ref}

def create_fallback_case(session_id, trigger_code, trigger_reason="",
    agent_id="system", institution_id="default", kyc_type="SIMPLIFIED",
    customer_name="", customer_mobile="", notes="", **kwargs):
    with db_session() as db:
        existing = db.query(FallbackCase).filter_by(session_id=session_id).first()
        if existing:
            d = _row(existing)
            return {"case":d,"already_exists":True}
        req_docs = REQUIRED_DOCS_REGULAR if kyc_type=="REGULAR" else REQUIRED_DOCS_SIMPLIFIED
        r = FallbackCase(
            case_id=f"FKYC-{str(uuid.uuid4())[:6].upper()}",
            session_id=session_id, trigger_code=trigger_code,
            trigger_reason=trigger_reason, agent_id=agent_id,
            institution_id=institution_id, kyc_type=kyc_type,
            customer_name=customer_name, customer_mobile=customer_mobile,
            status="INITIATED", required_docs=req_docs,
            submitted_docs=[], missing_docs=list(req_docs),
            history=[{"status":"INITIATED","timestamp":_nows(),"note":trigger_reason}],
            sla_hours=72, bfiu_ref="BFIU Circular No. 29 S1.2(d)",
        )
        db.add(r); db.flush()
        d = _row(r)
        return {"case":d,"already_exists":False}

def get_case(case_id=None, session_id=None):
    with db_session() as db:
        q = db.query(FallbackCase)
        if case_id:    q = q.filter_by(case_id=case_id)
        elif session_id: q = q.filter_by(session_id=session_id)
        r = q.first()
        if not r: return None
        d = _row(r)
        return {"case":d, **d}

def list_cases(status=None, limit=50):
    with db_session() as db:
        q = db.query(FallbackCase)
        if status: q = q.filter_by(status=status)
        return [_row(r) for r in q.order_by(FallbackCase.created_at.desc()).limit(limit).all()]

def submit_document(case_id, doc_type, doc_b64="", filename="", uploaded_by="customer"):
    if doc_type not in VALID_DOC_TYPES:
        return {"success":False,"error":f"Invalid doc_type: {doc_type!r}. Must be one of {sorted(VALID_DOC_TYPES)}"}
    with db_session() as db:
        r = db.query(FallbackCase).filter_by(case_id=case_id).first()
        if not r: return {"success":False,"error":"Case not found"}
        missing   = list(r.missing_docs or [])
        submitted = list(r.submitted_docs or [])
        if doc_type in missing:  missing.remove(doc_type)
        if doc_type not in submitted: submitted.append(doc_type)
        r.missing_docs   = missing
        r.submitted_docs = submitted
        hist = list(r.history or [])
        hist.append({"status":r.status,"timestamp":_nows(),"note":f"Doc submitted: {doc_type}"})
        r.history = hist
        if not missing and r.status not in ("UNDER_REVIEW","APPROVED","REJECTED"):
            r.status = "DOCS_SUBMITTED"
        d = _row(r)
        return {"success":True,"case":d,"missing_docs":missing,"submitted_docs":submitted, **d}

def start_review(case_id, reviewer_id="system"):
    with db_session() as db:
        r = db.query(FallbackCase).filter_by(case_id=case_id).first()
        if not r: return {"success":False,"error":"Case not found"}
        if r.missing_docs:
            return {"success":False,"error":f"Missing documents: {r.missing_docs}"}
        r.status = "UNDER_REVIEW"
        r.reviewer_id = reviewer_id
        hist = list(r.history or [])
        hist.append({"status":"UNDER_REVIEW","timestamp":_nows(),"reviewer":reviewer_id,"note":"Review started"})
        r.history = hist
        d = _row(r)
        return {"success":True,"case":d, **d}

def decide_case(case_id, reviewer_id, decision, note=""):
    if decision.upper() not in ("APPROVE","REJECT"):
        return {"success":False,"error":"decision must be APPROVE or REJECT"}
    with db_session() as db:
        r = db.query(FallbackCase).filter_by(case_id=case_id).first()
        if not r: return {"success":False,"error":"Case not found"}
        status = "APPROVED" if decision.upper()=="APPROVE" else "REJECTED"
        r.status = status
        r.reviewer_id = reviewer_id
        r.reviewer_note = note
        hist = list(r.history or [])
        hist.append({"status":status,"timestamp":_nows(),"reviewer":reviewer_id,"note":note})
        r.history = hist
        if status == "APPROVED": r.approved_at = _now()
        d = _row(r)
        return {"success":True,"case":d, **d}

def get_stats():
    with db_session() as db:
        rows = db.query(FallbackCase).all()
        statuses = ["INITIATED","DOCS_PENDING","DOCS_SUBMITTED","UNDER_REVIEW","APPROVED","REJECTED","COMPLETED"]
        counts = {s:len([r for r in rows if r.status==s]) for s in statuses}
        return {"total":len(rows),"by_status":counts,"pending":counts.get("INITIATED",0),**counts}

get_case_by_session = lambda sid: get_case(session_id=sid)
