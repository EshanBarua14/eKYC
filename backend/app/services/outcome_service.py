"""
Onboarding Outcome State Machine - M18 + M26
PostgreSQL backed via SQLAlchemy
"""
from datetime import datetime, timezone
from typing import Optional
import uuid, copy
from app.db.database import db_session
from app.db.models import OnboardingOutcome

STATES = {"PENDING","SCREENING","RISK_GRADED","APPROVED","PENDING_REVIEW","REJECTED","FALLBACK_KYC"}
TRANSITIONS = {
    "PENDING":        ["SCREENING","FALLBACK_KYC","REJECTED"],
    "SCREENING":      ["RISK_GRADED","REJECTED","FALLBACK_KYC"],
    "RISK_GRADED":    ["APPROVED","PENDING_REVIEW","REJECTED"],
    "PENDING_REVIEW": ["APPROVED","REJECTED"],
    "APPROVED":[], "REJECTED":[], "FALLBACK_KYC":["PENDING"],
}

def _now(): return datetime.now(timezone.utc)
def _nows(): return _now().isoformat()

def _row_to_dict(r):
    return {"outcome_id":r.outcome_id,"session_id":r.session_id,"state":r.state,
            "verdict":r.verdict,"confidence":r.confidence,"risk_grade":r.risk_grade,
            "risk_score":r.risk_score,"pep_flag":r.pep_flag,"edd_required":r.edd_required,
            "screening_result":r.screening_result,"kyc_type":r.kyc_type,
            "full_name":r.full_name,"agent_id":r.agent_id,"institution_id":r.institution_id,
            "checker_id":r.checker_id,"checker_note":r.checker_note,
            "auto_approved":r.auto_approved,"fallback_reason":r.fallback_reason,
            "history":r.history or [],"approved_at":str(r.approved_at) if r.approved_at else None,
            "rejected_at":str(r.rejected_at) if r.rejected_at else None,
            "updated_at":str(r.updated_at),"bfiu_ref":r.bfiu_ref}

def create_outcome(session_id, verdict, confidence, risk_grade="LOW", risk_score=0,
    pep_flag=False, edd_required=False, screening_result="CLEAR",
    kyc_type="SIMPLIFIED", full_name="N/A", agent_id="N/A", institution_id="N/A"):
    with db_session() as db:
        existing = db.query(OnboardingOutcome).filter_by(session_id=session_id).first()
        if existing:
            return {"error":"Outcome already exists","outcome":_row_to_dict(existing)}
        row = OnboardingOutcome(
            outcome_id=str(uuid.uuid4())[:8], session_id=session_id,
            state="PENDING", verdict=verdict, confidence=confidence,
            risk_grade=risk_grade, risk_score=risk_score, pep_flag=pep_flag,
            edd_required=edd_required, screening_result=screening_result,
            kyc_type=kyc_type, full_name=full_name, agent_id=agent_id,
            institution_id=institution_id,
            history=[{"state":"PENDING","timestamp":_nows(),"actor":"system","note":"Onboarding initiated"}],
            bfiu_ref="BFIU Circular No. 29")
        db.add(row); db.flush()
        return _row_to_dict(row)

def transition(session_id, to_state, actor="system", note=None):
    with db_session() as db:
        row = db.query(OnboardingOutcome).filter_by(session_id=session_id).first()
        if not row: return {"success":False,"error":f"No outcome for {session_id}"}
        if to_state not in STATES: return {"success":False,"error":f"Unknown state: {to_state}"}
        if to_state not in TRANSITIONS.get(row.state,[]):
            return {"success":False,"error":f"Invalid: {row.state}->{to_state}","allowed":TRANSITIONS.get(row.state,[])}
        row.state = to_state; row.updated_at = _now()
        hist = list(copy.deepcopy(row.history) if row.history else [])
        hist.append({"state":to_state,"timestamp":_nows(),"actor":actor,"note":note or ""})
        row.history = hist
        if to_state == "APPROVED": row.approved_at = _now()
        elif to_state == "REJECTED": row.rejected_at = _now()
        return {"success":True,"outcome":_row_to_dict(row)}

def auto_route(session_id):
    rec = get_outcome(session_id)
    if not rec: return {"success":False,"error":"Outcome not found"}
    # Already in terminal state — return success idempotently
    if rec["state"] == "APPROVED":
        return {"success":True,"outcome":rec,"auto_approved":True}
    if rec["state"] == "REJECTED":
        return {"success":True,"outcome":rec,"auto_approved":False}
    if rec["state"] == "PENDING":
        transition(session_id, "SCREENING", note="Background checks started")
        rec = get_outcome(session_id)
    if rec["state"] == "SCREENING":
        transition(session_id, "RISK_GRADED", note="Risk score assigned")
        rec = get_outcome(session_id)
    v=rec["verdict"]; rg=rec["risk_grade"]; pep=rec["pep_flag"]
    edd=rec["edd_required"]; sr=rec["screening_result"]
    if v=="FAILED": return transition(session_id,"REJECTED",note="Face match FAILED")
    if sr=="BLOCKED": return transition(session_id,"REJECTED",note="Sanctions hit")
    if v=="MATCHED" and rg=="LOW" and not pep and not edd and sr=="CLEAR":
        r=transition(session_id,"APPROVED",note="Auto-approved: low risk")
        r["auto_approved"]=True; return r
    reason=[]
    if rg in("HIGH","MEDIUM"): reason.append(f"Risk:{rg}")
    if pep: reason.append("PEP")
    if edd: reason.append("EDD required")
    r=transition(session_id,"PENDING_REVIEW",note=f"Checker queue: {chr(44).join(reason)}")
    r["auto_approved"]=False; r["review_reasons"]=reason; return r

def checker_decide(session_id, checker_id, decision, note=None):
    with db_session() as db:
        row = db.query(OnboardingOutcome).filter_by(session_id=session_id).first()
        if not row: return {"success":False,"error":"Outcome not found"}
        if row.state != "PENDING_REVIEW": return {"success":False,"error":f"State is {row.state}"}
        if decision.upper() not in ("APPROVE","REJECT"): return {"success":False,"error":"Must be APPROVE or REJECT"}
        row.checker_id = checker_id; row.checker_note = note
    return transition(session_id,"APPROVED" if decision.upper()=="APPROVE" else "REJECTED",actor=checker_id,note=note)

def trigger_fallback(session_id, reason="EC API unavailable"):
    with db_session() as db:
        row = db.query(OnboardingOutcome).filter_by(session_id=session_id).first()
        if not row: return {"success":False,"error":"Outcome not found"}
        row.state="FALLBACK_KYC"; row.updated_at=_now(); row.fallback_reason=reason
        hist=list(row.history or [])
        hist.append({"state":"FALLBACK_KYC","timestamp":_nows(),"actor":"system","note":reason})
        row.history=hist
        return {"success":True,"outcome":_row_to_dict(row),"fallback_triggered":True}

def get_outcome(session_id):
    with db_session() as db:
        row = db.query(OnboardingOutcome).filter_by(session_id=session_id).first()
        return _row_to_dict(row) if row else None

def list_outcomes(state=None, limit=100):
    with db_session() as db:
        q = db.query(OnboardingOutcome)
        if state: q = q.filter(OnboardingOutcome.state==state)
        return [_row_to_dict(r) for r in q.order_by(OnboardingOutcome.created_at.desc()).limit(limit).all()]

def get_queue_summary():
    with db_session() as db:
        rows = db.query(OnboardingOutcome).all()
        return {s:len([r for r in rows if r.state==s]) for s in STATES}
