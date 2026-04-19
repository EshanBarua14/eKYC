"""
CMI / BO Account Routes - M20
BFIU Circular No. 29 — Section 6.2 (Capital Markets, 2026)

POST /cmi/bo/open          - Open BO account after eKYC
GET  /cmi/bo/{bo_number}   - Get BO account details
GET  /cmi/bo/session/{sid} - Get BO account by session
GET  /cmi/bo/list          - List all BO accounts
GET  /cmi/thresholds       - 2026 CMI thresholds
GET  /cmi/products         - BO product catalog
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.cmi_service import (
    open_bo_account, get_bo_account, get_bo_by_session,
    list_bo_accounts, get_threshold_info,
    BO_PRODUCTS, CMI_THRESHOLDS_2026,
)

router = APIRouter(prefix="/cmi", tags=["CMI BO Account"])


class BOAccountRequest(BaseModel):
    session_id:     str
    kyc_verdict:    str
    confidence:     float
    full_name:      str
    nid_hash:       str
    mobile:         str
    date_of_birth:  str
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
    """
    Open CDBL BO account after successful eKYC.
    Applies 2026 BFIU threshold: BDT 15,00,000 for Simplified.
    Above threshold -> Regular eKYC required.
    """
    if req.kyc_verdict not in ("MATCHED", "REVIEW", "FAILED"):
        raise HTTPException(400, "kyc_verdict must be MATCHED, REVIEW, or FAILED")

    result = open_bo_account(**req.model_dump())

    if not result.get("success"):
        raise HTTPException(422, result.get("error", "BO account opening failed"))

    return {
        **result,
        "bfiu_ref":  "BFIU Circular No. 29 — Section 6.2 (2026)",
        "threshold": CMI_THRESHOLDS_2026["bo_simplified_max_deposit"],
    }


@router.get("/bo/list",              operation_id="cmi_bo_list")
async def cmi_list_accounts(
    status: Optional[str] = None,
    limit:  int = Query(50, le=200),
):
    """List BO accounts optionally filtered by status."""
    accounts = list_bo_accounts(status, limit)
    return {"accounts": accounts, "total": len(accounts)}


@router.get("/thresholds",           operation_id="cmi_get_thresholds")
async def cmi_thresholds():
    """2026 BFIU CMI thresholds and product catalog."""
    return get_threshold_info()


@router.get("/products",             operation_id="cmi_get_products")
async def cmi_products():
    """BO product catalog with KYC type requirements."""
    return {
        "products": BO_PRODUCTS,
        "total":    len(BO_PRODUCTS),
        "bfiu_ref": "BFIU Circular No. 29 — Section 6.2 (2026)",
    }


@router.get("/bo/session/{session_id}", operation_id="cmi_bo_by_session")
async def cmi_get_by_session(session_id: str):
    """Get BO account by eKYC session ID."""
    account = get_bo_by_session(session_id)
    if not account:
        raise HTTPException(404, f"No BO account for session '{session_id}'")
    return {"bo_account": account}


@router.get("/bo/{bo_number}",       operation_id="cmi_bo_by_number")
async def cmi_get_account(bo_number: str):
    """Get BO account by BO number."""
    account = get_bo_account(bo_number)
    if not account:
        raise HTTPException(404, f"BO account '{bo_number}' not found")
    return {"bo_account": account}
