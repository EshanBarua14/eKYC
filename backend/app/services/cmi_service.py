"""CMI/BO Account Service - M20 + M26 PostgreSQL backed"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models import BOAccount

SIMPLIFIED_THRESHOLD_BDT = 1_500_000
CMI_PRODUCTS = {
    "BO_ACCOUNT":     {"name":"Beneficial Owner (BO) Account","cdbl_code":"BO001","threshold":1500000},
    "BO_INDIVIDUAL":  {"name":"BO Account - Individual","cdbl_code":"BO-IND","threshold":1500000},
    "BO_JOINT":       {"name":"BO Account - Joint","cdbl_code":"BO-JNT","threshold":0},
    "BO_NRB":         {"name":"BO Account - NRB","cdbl_code":"BO-NRB","threshold":0},
    "MARGIN_LOAN":    {"name":"Margin Loan Account","cdbl_code":"ML001","threshold":0},
    "MARGIN_ACCOUNT": {"name":"Margin Account","cdbl_code":"ML002","threshold":0},
    "PORTFOLIO_MGT":  {"name":"Portfolio Management Account","cdbl_code":"PM001","threshold":0},
}
_ALWAYS_REGULAR = {"BO_JOINT","BO_NRB","MARGIN_LOAN","MARGIN_ACCOUNT"}

def _now(): return datetime.now(timezone.utc)

def _row(r):
    # Normalize legacy statuses
    status = r.status
    if status == "AUTO_APPROVED": status = "ACTIVE"
    # Normalize legacy bo_number formats (old: BOxxxxxxxx, new: 1201xxxxxxxx)
    bo_number = r.bo_number
    if bo_number and not bo_number.startswith("1201"):
        bo_number = f"1201{bo_number[-8:]}"
    return {"bo_number":bo_number,"cdbl_ref":r.cdbl_ref,"session_id":r.session_id,
            "full_name":r.full_name,"mobile":r.mobile,"email":r.email,
            "product_type":r.product_type,"deposit_amount":r.deposit_amount,
            "kyc_type":r.kyc_type,"kyc_verdict":r.kyc_verdict,"confidence":r.confidence,
            "risk_grade":r.risk_grade,"status":status,"auto_approved":r.auto_approved,
            "institution_id":r.institution_id,"nominee_name":r.nominee_name,
            "cdbl_code":r.cdbl_code,"created_at":str(r.created_at),"bfiu_ref":r.bfiu_ref}

def open_bo_account(session_id, full_name, mobile, date_of_birth, nid_hash=None,
    product_type="BO_ACCOUNT", deposit_amount=0.0, kyc_verdict="MATCHED",
    confidence=0.0, risk_grade="LOW", risk_score=0, pep_flag=False,
    institution_id="default", agent_id="system", email="", nominee_name="", joint_holder=""):
    if kyc_verdict == "FAILED":
        return {"error":"FAILED verdict cannot open BO account","code":"FAILED_VERDICT"}
    prod = CMI_PRODUCTS.get(product_type, CMI_PRODUCTS["BO_ACCOUNT"])
    kyc_type = "REGULAR" if (pep_flag or deposit_amount > SIMPLIFIED_THRESHOLD_BDT or product_type in _ALWAYS_REGULAR) else "SIMPLIFIED"
    auto = (kyc_verdict=="MATCHED" and risk_grade=="LOW" and not pep_flag and kyc_type=="SIMPLIFIED")
    with db_session() as db:
        existing = db.query(BOAccount).filter_by(session_id=session_id).first()
        if existing:
            return {"already_exists":True,"bo_account":_row(existing),"kyc_type":existing.kyc_type,"auto_approved":existing.auto_approved,"bo_number":existing.bo_number}
        bo_num   = f"1201{str(uuid.uuid4())[:8].upper()}"
        cdbl_ref = f"CDBL-{str(uuid.uuid4())[:8].upper()}"
        r = BOAccount(
            bo_number=bo_num,session_id=session_id,full_name=full_name,
            mobile=mobile,email=email,date_of_birth=date_of_birth,
            product_type=product_type,product_name=prod["name"],
            cdbl_code=prod.get("cdbl_code","BO001"),cdbl_ref=cdbl_ref,
            deposit_amount=deposit_amount,kyc_type=kyc_type,kyc_verdict=kyc_verdict,
            confidence=confidence,risk_grade=risk_grade,risk_score=risk_score,
            pep_flag=pep_flag,status="ACTIVE" if auto else "PENDING_REVIEW",
            auto_approved=auto,institution_id=institution_id,agent_id=agent_id,
            nominee_name=nominee_name,joint_holder=joint_holder,
            threshold_2026=True,bfiu_ref="BFIU Circular No. 29 S5 (CMI)")
        db.add(r); db.flush()
        return {"bo_account":_row(r),"kyc_type":kyc_type,"auto_approved":auto,"bo_number":bo_num}

def get_account(bo_number=None, session_id=None):
    with db_session() as db:
        q = db.query(BOAccount)
        if bo_number: q = q.filter_by(bo_number=bo_number)
        elif session_id: q = q.filter_by(session_id=session_id)
        r = q.first(); return _row(r) if r else None

def list_accounts(status=None, limit=50):
    with db_session() as db:
        q = db.query(BOAccount)
        if status: q = q.filter_by(status=status)
        return [_row(r) for r in q.order_by(BOAccount.created_at.desc()).limit(limit).all()]

def get_stats():
    with db_session() as db:
        total   = db.query(BOAccount).count()
        active  = db.query(BOAccount).filter_by(status="ACTIVE").count()
        pending = db.query(BOAccount).filter_by(status="PENDING_REVIEW").count()
        return {"total":total,"auto_approved":active,"pending_review":pending,"threshold_bdt":SIMPLIFIED_THRESHOLD_BDT}

get_bo_account     = get_account
get_bo_by_session  = lambda sid: get_account(session_id=sid)
list_bo_accounts   = list_accounts
get_threshold_info = get_stats
BO_PRODUCTS        = CMI_PRODUCTS
CMI_THRESHOLDS_2026 = {"SIMPLIFIED":1500000,"REGULAR":99999999}
