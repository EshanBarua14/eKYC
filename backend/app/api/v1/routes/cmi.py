"""CMI / BO Account Routes - M20"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.cmi_service import (
    open_bo_account, get_bo_account, get_bo_by_session,
    list_bo_accounts, get_threshold_info,
    BO_PRODUCTS, CMI_PRODUCTS, CMI_THRESHOLDS_2026,
)

router = APIRouter(prefix="/cmi", tags=["CMI BO Account"])

class BOAccountRequest(BaseModel):
    session_id:     str
    kyc_verdict:    str
    confidence:     float
    full_name:      str
    nid_hash:       str = ""
    mobile:         str
    date_of_birth:  str = ""
    product_type:   str   = "BO_INDIVIDUAL"
    deposit_amount: float = 0.0
    risk_grade:     str   = "LOW"
    risk_score:     int   = 0
    pep_flag:       bool  = False
    institution_id: str   = "N/A"
    agent_id:       str   = "N/A"
    email:          Optional[str] = None
    nominee_name:   Optional[str] = None
    joint_holder:   Optional[str] = None

@router.post("/bo/open", status_code=201, operation_id="cmi_bo_open")
async def cmi_open_account(req: BOAccountRequest):
    if req.kyc_verdict not in ("MATCHED", "REVIEW", "FAILED"):
        raise HTTPException(400, "kyc_verdict must be MATCHED, REVIEW, or FAILED")
    known = ["session_id","full_name","mobile","date_of_birth","product_type",
             "deposit_amount","kyc_verdict","confidence","risk_grade","risk_score",
             "pep_flag","institution_id","agent_id","email","nominee_name","joint_holder","nid_hash"]
    result = open_bo_account(**{k: v for k, v in req.model_dump().items() if k in known})
    if result.get("error") and not result.get("already_exists"):
        raise HTTPException(422, result.get("error", "BO account opening failed"))
    return {**result, "bfiu_ref": "BFIU Circular No. 29 Section 6.2 (2026)", "threshold": 1500000}

@router.get("/bo/list", operation_id="cmi_bo_list")
async def cmi_list_accounts(status: Optional[str] = None, limit: int = Query(50, le=200)):
    accounts = list_bo_accounts(status, limit)
    return {"accounts": accounts, "total": len(accounts)}

@router.get("/thresholds", operation_id="cmi_thresholds")
async def cmi_thresholds():
    return {"simplified_max_bdt":1500000,"regular_min_bdt":1500001,
            "threshold_2026":True,"products":list(CMI_PRODUCTS.keys()),
            "bfiu_ref":"BFIU Circular No. 29"}

@router.get("/bo/session/{session_id}", operation_id="cmi_bo_by_session")
async def cmi_get_by_session(session_id: str):
    account = get_bo_by_session(session_id)
    if not account:
        raise HTTPException(404, f"No BO account for session {session_id!r}")
    return {"bo_account": account}

@router.get("/bo/{bo_number}", operation_id="cmi_bo_by_number")
async def cmi_get_account(bo_number: str):
    account = get_bo_account(bo_number)
    if not account:
        raise HTTPException(404, f"BO account {bo_number!r} not found")
    return {"bo_account": account}

@router.get("/products", operation_id="cmi_products")
async def cmi_products():
    return {"products": CMI_PRODUCTS, "bfiu_ref": "BFIU Circular No. 29"}
