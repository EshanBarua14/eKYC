"""
Xpert Fintech eKYC Platform
Risk Grading Routes - M8
POST /risk/grade        - Calculate risk score for a KYC profile
POST /risk/edd          - Create EDD case for HIGH risk profile
GET  /risk/factors      - List all scoring dimensions and options
GET  /risk/thresholds   - Current BFIU thresholds
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.services.risk_grading_service import (
    calculate_risk_score, create_edd_case, rescore_profile,
    ONBOARDING_CHANNEL_SCORES, RESIDENCY_SCORES, PEP_IP_SCORES,
    PRODUCT_RISK_SCORES_INSURANCE, PRODUCT_RISK_SCORES_CMI,
    BUSINESS_TYPE_SCORES, PROFESSION_SCORES, TRANSPARENCY_SCORES,
    HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD, REVIEW_FREQUENCY,
)

router   = APIRouter(prefix="/risk", tags=["Risk Grading"])
security = HTTPBearer()

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class RiskGradeRequest(BaseModel):
    kyc_profile_id:     str
    institution_type:   str = "INSURANCE"
    onboarding_channel: str = "AGENCY"
    residency:          str = "RESIDENT"
    pep_ip_status:      str = "NONE"
    product_type:       str = "ORDINARY_LIFE"
    business_type:      str = "OTHER"
    profession:         str = "OTHER"
    annual_income_bdt:  float = 0.0
    source_of_funds:    Optional[str] = None
    pep_flag:           bool = False
    adverse_media:      bool = False

class EDDCaseRequest(BaseModel):
    kyc_profile_id:  str
    institution_id:  str
    risk_score:      int
    risk_grade:      str
    pep_override:    bool = False
    adverse_media:   bool = False

class RescoreRequest(BaseModel):
    profile_data: dict

# ---------------------------------------------------------------------------
# POST /risk/grade
# ---------------------------------------------------------------------------
@router.post("/grade")
def grade_risk(
    req: RiskGradeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Calculate risk score for a KYC profile.
    Returns score, grade, EDD flag, dimension breakdown.
    HIGH score (>=15) or PEP/IP flag triggers EDD.
    """
    result = calculate_risk_score(
        onboarding_channel = req.onboarding_channel,
        residency          = req.residency,
        pep_ip_status      = req.pep_ip_status,
        product_type       = req.product_type,
        business_type      = req.business_type,
        profession         = req.profession,
        annual_income_bdt  = req.annual_income_bdt,
        source_of_funds    = req.source_of_funds,
        institution_type   = req.institution_type,
        pep_flag           = req.pep_flag,
        adverse_media      = req.adverse_media,
    )

    return {
        "kyc_profile_id": req.kyc_profile_id,
        **result,
    }

# ---------------------------------------------------------------------------
# POST /risk/edd
# ---------------------------------------------------------------------------
@router.post("/edd", status_code=201)
def create_edd(
    req: EDDCaseRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create an EDD case for a HIGH risk profile.
    Only valid for HIGH risk profiles (grade=HIGH or pep_override=True).
    """
    if req.risk_grade != "HIGH" and not req.pep_override and not req.adverse_media:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "EDD_NOT_REQUIRED",
                "message":    "EDD is only required for HIGH risk profiles",
            }
        )

    case = create_edd_case(
        kyc_profile_id = req.kyc_profile_id,
        risk_result    = {
            "total_score":   req.risk_score,
            "grade":         req.risk_grade,
            "pep_override":  req.pep_override,
            "adverse_media": req.adverse_media,
        },
        institution_id = req.institution_id,
    )
    return case

# ---------------------------------------------------------------------------
# POST /risk/rescore
# ---------------------------------------------------------------------------
@router.post("/rescore")
def rescore(
    req: RescoreRequest,
    current_user: dict = Depends(get_current_user),
):
    """Re-score a KYC profile using stored fields. Used by lifecycle manager."""
    result = rescore_profile(req.profile_data)
    return result

# ---------------------------------------------------------------------------
# GET /risk/factors
# ---------------------------------------------------------------------------
@router.get("/factors")
def list_factors(current_user: dict = Depends(get_current_user)):
    """List all scoring dimensions, options and scores."""
    return {
        "d1_onboarding_channel":     ONBOARDING_CHANNEL_SCORES,
        "d2_residency":              RESIDENCY_SCORES,
        "d3_pep_ip_status":          PEP_IP_SCORES,
        "d4_product_insurance":      PRODUCT_RISK_SCORES_INSURANCE,
        "d4_product_cmi":            PRODUCT_RISK_SCORES_CMI,
        "d5a_business_type":         BUSINESS_TYPE_SCORES,
        "d5b_profession":            PROFESSION_SCORES,
        "d7_transparency":           TRANSPARENCY_SCORES,
        "d6_transaction_bands": {
            "below_1M_BDT":   1,
            "1M_to_5M_BDT":   2,
            "5M_to_50M_BDT":  3,
            "above_50M_BDT":  5,
        },
        "bfiu_ref": "BFIU Circular No. 29 - Section 6.3",
    }

# ---------------------------------------------------------------------------
# GET /risk/thresholds
# ---------------------------------------------------------------------------
@router.get("/thresholds")
def get_thresholds(current_user: dict = Depends(get_current_user)):
    """Return current BFIU risk thresholds and review frequencies."""
    return {
        "high_risk_threshold":   HIGH_RISK_THRESHOLD,
        "medium_risk_threshold": MEDIUM_RISK_THRESHOLD,
        "grades": {
            "HIGH":   f"score >= {HIGH_RISK_THRESHOLD}",
            "MEDIUM": f"score >= {MEDIUM_RISK_THRESHOLD} and < {HIGH_RISK_THRESHOLD}",
            "LOW":    f"score < {MEDIUM_RISK_THRESHOLD}",
        },
        "review_frequency_years": REVIEW_FREQUENCY,
        "overrides": [
            "PEP flag -> HIGH regardless of score",
            "IP flag -> HIGH regardless of score",
            "Adverse media -> HIGH regardless of score",
        ],
        "edd_trigger":  "grade == HIGH",
        "bfiu_ref":     "BFIU Circular No. 29 - Section 6.3",
    }
