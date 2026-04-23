"""
Compliance Dashboard API - M14
GET  /compliance/posture          - Overall compliance posture summary
GET  /compliance/kyc-queues       - Pending review queues by risk grade
GET  /compliance/edd-cases        - EDD cases awaiting action
GET  /compliance/screening-hits   - Recent sanctions/PEP/adverse media hits
GET  /compliance/failed-onboarding - Failed onboarding summary
GET  /compliance/export           - BFIU export JSON or CSV
GET  /compliance/metrics          - Time-series metrics last 30 days
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
import random

router = APIRouter(prefix="/compliance", tags=["compliance"])

def _now(): return datetime.now(timezone.utc)
def _iso(dt): return dt.isoformat()
def _days_ago(n): return _iso(_now() - timedelta(days=n))

_KYC_QUEUES = [
    {"id":"kyc_001","customer_name":"Md. Rahman Hossain", "nid":"1991********3421","risk_grade":"HIGH",  "score":18,"kyc_type":"REGULAR",   "due_date":_days_ago(-2),"status":"OVERDUE",  "agent":"agent_01"},
    {"id":"kyc_002","customer_name":"Farida Begum",       "nid":"1985********7821","risk_grade":"HIGH",  "score":16,"kyc_type":"REGULAR",   "due_date":_days_ago(-1),"status":"OVERDUE",  "agent":"agent_02"},
    {"id":"kyc_003","customer_name":"Karim Uddin Ahmed",  "nid":"1978********2341","risk_grade":"MEDIUM","score":10,"kyc_type":"SIMPLIFIED","due_date":_days_ago(5), "status":"PENDING",  "agent":"agent_01"},
    {"id":"kyc_004","customer_name":"Sultana Razia",      "nid":"1990********5671","risk_grade":"MEDIUM","score":11,"kyc_type":"SIMPLIFIED","due_date":_days_ago(12),"status":"PENDING",  "agent":"agent_03"},
    {"id":"kyc_005","customer_name":"Abu Bakar Siddique", "nid":"1982********8901","risk_grade":"LOW",   "score":4, "kyc_type":"SIMPLIFIED","due_date":_days_ago(30),"status":"PENDING",  "agent":"agent_02"},
    {"id":"kyc_006","customer_name":"Nasrin Akhter",      "nid":"1995********1121","risk_grade":"LOW",   "score":3, "kyc_type":"SIMPLIFIED","due_date":_days_ago(45),"status":"PENDING",  "agent":"agent_04"},
    {"id":"kyc_007","customer_name":"Jahangir Alam",      "nid":"1975********3341","risk_grade":"HIGH",  "score":20,"kyc_type":"REGULAR",   "due_date":_days_ago(0), "status":"DUE_TODAY","agent":"agent_01"},
]

_EDD_CASES = [
    {"id":"edd_001","customer_name":"Md. Rahman Hossain","risk_score":18,"trigger":"HIGH_RISK_SCORE","pep":False,"adverse_media":False,"opened":_days_ago(5), "status":"OPEN",      "assigned_to":"checker_01"},
    {"id":"edd_002","customer_name":"Shaheed Kamal",     "risk_score":22,"trigger":"PEP_OVERRIDE",  "pep":True, "adverse_media":False,"opened":_days_ago(12),"status":"IN_REVIEW", "assigned_to":"checker_02"},
    {"id":"edd_003","customer_name":"Farida Begum",      "risk_score":16,"trigger":"HIGH_RISK_SCORE","pep":False,"adverse_media":True, "opened":_days_ago(3), "status":"OPEN",      "assigned_to":"checker_01"},
    {"id":"edd_004","customer_name":"Monir Hossain",     "risk_score":19,"trigger":"ADVERSE_MEDIA",  "pep":False,"adverse_media":True, "opened":_days_ago(20),"status":"ESCALATED", "assigned_to":"checker_03"},
    {"id":"edd_005","customer_name":"Roksana Parvin",    "risk_score":15,"trigger":"HIGH_RISK_SCORE","pep":False,"adverse_media":False,"opened":_days_ago(1), "status":"OPEN",      "assigned_to":"checker_01"},
]

_SCREENING_HITS = [
    {"id":"scr_001","customer_name":"Ali Hassan Al-Rashid","check_type":"UNSCR",        "match_score":0.91,"verdict":"BLOCKED","matched_list":"UN Consolidated List",    "timestamp":_days_ago(1),"agent":"agent_02"},
    {"id":"scr_002","customer_name":"Md. Kamal Pasha",     "check_type":"PEP",          "match_score":0.85,"verdict":"REVIEW", "matched_list":"Bangladesh PEP Registry", "timestamp":_days_ago(2),"agent":"agent_01"},
    {"id":"scr_003","customer_name":"Sultana Razia",       "check_type":"ADVERSE_MEDIA","match_score":0.78,"verdict":"REVIEW", "matched_list":"Adverse Media DB",        "timestamp":_days_ago(3),"agent":"agent_03"},
    {"id":"scr_004","customer_name":"Jamal Uddin",         "check_type":"EXIT_LIST",    "match_score":1.00,"verdict":"BLOCKED","matched_list":"Institution Exit List",   "timestamp":_days_ago(4),"agent":"agent_01"},
    {"id":"scr_005","customer_name":"Nur Mohammad",        "check_type":"UNSCR",        "match_score":0.72,"verdict":"REVIEW", "matched_list":"UN Consolidated List",    "timestamp":_days_ago(5),"agent":"agent_04"},
]

_FAILED_ONBOARDING = [
    {"id":"fail_001","customer_name":"Unknown Customer 1","step":"NID_VERIFICATION","reason":"NID not found in EC database",          "attempts":3, "timestamp":_days_ago(1),"agent":"agent_01"},
    {"id":"fail_002","customer_name":"Unknown Customer 2","step":"FACE_MATCH",      "reason":"Face match confidence below threshold",  "attempts":1, "timestamp":_days_ago(1),"agent":"agent_02"},
    {"id":"fail_003","customer_name":"Unknown Customer 3","step":"LIVENESS",        "reason":"Liveness challenge failed 3 times",      "attempts":3, "timestamp":_days_ago(2),"agent":"agent_01"},
    {"id":"fail_004","customer_name":"Unknown Customer 4","step":"FINGERPRINT",     "reason":"Fingerprint mismatch fallback triggered", "attempts":2, "timestamp":_days_ago(2),"agent":"agent_03"},
    {"id":"fail_005","customer_name":"Unknown Customer 5","step":"SCREENING",       "reason":"UNSCR sanctions hit onboarding blocked",  "attempts":1, "timestamp":_days_ago(3),"agent":"agent_02"},
    {"id":"fail_006","customer_name":"Unknown Customer 6","step":"NID_VERIFICATION","reason":"Session limit exceeded 10 attempts",      "attempts":10,"timestamp":_days_ago(3),"agent":"agent_04"},
]

@router.get("/posture")
async def compliance_posture():
    overdue = [k for k in _KYC_QUEUES if k["status"]=="OVERDUE"]
    return {
        "generated_at": _iso(_now()),
        "bfiu_ref": "BFIU Circular No. 29",
        "kyc_reviews": {
            "total_pending": len(_KYC_QUEUES),
            "high_risk":     len([k for k in _KYC_QUEUES if k["risk_grade"]=="HIGH"]),
            "medium_risk":   len([k for k in _KYC_QUEUES if k["risk_grade"]=="MEDIUM"]),
            "low_risk":      len([k for k in _KYC_QUEUES if k["risk_grade"]=="LOW"]),
            "overdue":       len(overdue),
        },
        "edd": {
            "total_open": len([e for e in _EDD_CASES if e["status"]=="OPEN"]),
            "in_review":  len([e for e in _EDD_CASES if e["status"]=="IN_REVIEW"]),
            "escalated":  len([e for e in _EDD_CASES if e["status"]=="ESCALATED"]),
        },
        "screening": {
            "total_hits": len(_SCREENING_HITS),
            "blocked":    len([s for s in _SCREENING_HITS if s["verdict"]=="BLOCKED"]),
            "review":     len([s for s in _SCREENING_HITS if s["verdict"]=="REVIEW"]),
        },
        "failed_onboarding": {
            "total":    len(_FAILED_ONBOARDING),
            "last_24h": len([f for f in _FAILED_ONBOARDING if f["timestamp"] >= _days_ago(1)]),
        },
        "overall_status": "ACTION_REQUIRED" if overdue or any(e["status"]=="ESCALATED" for e in _EDD_CASES) else "REVIEW_PENDING",
    }

@router.get("/kyc-queues")
async def kyc_queues(grade: Optional[str]=None, status: Optional[str]=None):
    items = list(_KYC_QUEUES)
    if grade:  items = [k for k in items if k["risk_grade"]==grade.upper()]
    if status: items = [k for k in items if k["status"]==status.upper()]
    return {
        "queues": items, "total": len(items),
        "summary": {
            "HIGH":    len([k for k in _KYC_QUEUES if k["risk_grade"]=="HIGH"]),
            "MEDIUM":  len([k for k in _KYC_QUEUES if k["risk_grade"]=="MEDIUM"]),
            "LOW":     len([k for k in _KYC_QUEUES if k["risk_grade"]=="LOW"]),
            "OVERDUE": len([k for k in _KYC_QUEUES if k["status"]=="OVERDUE"]),
        },
        "review_intervals_years": {"HIGH":1,"MEDIUM":2,"LOW":5},
        "bfiu_ref": "BFIU Circular No. 29 - Section 6.3",
    }

@router.get("/edd-cases")
async def edd_cases(status: Optional[str]=None):
    items = list(_EDD_CASES)
    if status: items = [e for e in items if e["status"]==status.upper()]
    return {"cases": items, "total": len(items), "bfiu_ref": "BFIU Circular No. 29 - Section 6.3"}

@router.get("/screening-hits")
async def screening_hits(verdict: Optional[str]=None, check_type: Optional[str]=None):
    items = list(_SCREENING_HITS)
    if verdict:    items = [s for s in items if s["verdict"]==verdict.upper()]
    if check_type: items = [s for s in items if s["check_type"]==check_type.upper()]
    return {"hits": items, "total": len(items), "bfiu_ref": "BFIU Circular No. 29 - Section 5"}

@router.get("/failed-onboarding")
async def failed_onboarding(step: Optional[str]=None):
    items = list(_FAILED_ONBOARDING)
    if step: items = [f for f in items if f["step"]==step.upper()]
    by_step = {}
    for f in _FAILED_ONBOARDING:
        by_step[f["step"]] = by_step.get(f["step"],0)+1
    return {"failures": items, "total": len(items), "by_step": by_step}

@router.get("/export")
async def export_report(
    fmt:       str = Query("json", pattern="^(json|csv)$"),
    date_from: Optional[str] = None,
    date_to:   Optional[str] = None,
):
    data = {
        "export_date": _iso(_now()), "date_from": date_from or _days_ago(30),
        "date_to": date_to or _iso(_now()), "bfiu_ref": "BFIU Circular No. 29",
        "kyc_reviews_pending": len(_KYC_QUEUES),
        "edd_open":            len([e for e in _EDD_CASES if e["status"]=="OPEN"]),
        "screening_hits":      len(_SCREENING_HITS),
        "screening_blocked":   len([s for s in _SCREENING_HITS if s["verdict"]=="BLOCKED"]),
        "failed_onboarding":   len(_FAILED_ONBOARDING),
        "edd_cases":           _EDD_CASES,
        "screening_hits_detail":    _SCREENING_HITS,
        "failed_onboarding_detail": _FAILED_ONBOARDING,
    }
    if fmt == "csv":
        lines = ["section,id,customer_name,detail,status,timestamp"]
        for e in _EDD_CASES:
            lines.append(f"EDD,{e['id']},{e['customer_name']},{e['trigger']},{e['status']},{e['opened']}")
        for s in _SCREENING_HITS:
            lines.append(f"SCREENING,{s['id']},{s['customer_name']},{s['check_type']},{s['verdict']},{s['timestamp']}")
        for f in _FAILED_ONBOARDING:
            lines.append(f"FAILED,{f['id']},{f['customer_name']},{f['step']},FAILED,{f['timestamp']}")
        return {"format":"csv","data":"\n".join(lines)}
    return {"format":"json","data":data}

@router.get("/metrics")
async def metrics():
    random.seed(42)
    days = []
    for i in range(29,-1,-1):
        days.append({
            "date":            (_now()-timedelta(days=i)).strftime("%m/%d"),
            "onboarding_ok":   random.randint(8,35),
            "onboarding_fail": random.randint(0,5),
            "screening_hits":  random.randint(0,3),
            "edd_triggered":   random.randint(0,2),
        })
    return {"days": days, "period": "last_30_days"}

# In-memory EDD state mutations
_EDD_ACTIONS = {}  # action_id -> action record

@router.post("/edd-cases/{case_id}/action")
async def edd_case_action(case_id: str, body: dict):
    """
    Update EDD case status.
    action: ASSIGN | START_REVIEW | ESCALATE | CLOSE
    """
    from pydantic import BaseModel
    case = next((e for e in _EDD_CASES if e["id"]==case_id), None)
    if not case:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="EDD case not found")

    action    = body.get("action","").upper()
    note      = body.get("note","")
    actor     = body.get("actor","checker")

    TRANSITIONS = {
        "ASSIGN":       ("OPEN",      "IN_REVIEW"),
        "START_REVIEW": ("OPEN",      "IN_REVIEW"),
        "ESCALATE":     ("IN_REVIEW", "ESCALATED"),
        "CLOSE":        ("IN_REVIEW", "CLOSED"),
        "CLOSE_OPEN":   ("OPEN",      "CLOSED"),
    }

    if action not in TRANSITIONS:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Unknown action: {action}. Valid: {list(TRANSITIONS)}")

    expected_from, new_status = TRANSITIONS[action]
    # Allow CLOSE from either OPEN or IN_REVIEW
    if action == "CLOSE" and case["status"] == "OPEN":
        new_status = "CLOSED"
    elif case["status"] != expected_from and not (action=="CLOSE" and case["status"] in ("OPEN","IN_REVIEW")):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Cannot {action} case in status {case['status']}")

    case["status"]      = new_status
    case["assigned_to"] = actor
    case["last_action"] = {"action":action, "note":note, "actor":actor, "at":_iso(_now())}

    return {"success": True, "case_id": case_id, "new_status": new_status, "bfiu_ref": "BFIU Circular No. 29 - Section 6.3"}
