"""
Xpert Fintech eKYC Platform
Risk Grading Engine - M8
BFIU Circular No. 29 - Section 6.3.1 (Insurance) and 6.3.2 (CMI)
7 risk dimensions, admin-configurable scoring tables
Score >= 15 -> HIGH risk -> EDD mandatory
PEP/IP flag -> HIGH risk override regardless of score
"""
from typing import Optional

# ---------------------------------------------------------------------------
# Configurable scoring tables (admin can override via DB in prod)
# ---------------------------------------------------------------------------

# Dimension 1: Onboarding channel
ONBOARDING_CHANNEL_SCORES = {
    "AGENCY":           2,
    "BANK":             2,
    "EMPLOYEE_GROUP":   2,
    "DIGITAL_DIRECT":   2,
    "WALK_IN":          3,
    "SELF_CHECKIN":     2,
    "BRANCH_RM":        2,
    "DSA":              2,
}

# Dimension 2: Geographic/residency risk
RESIDENCY_SCORES = {
    "RESIDENT":  1,
    "NRB":       3,   # Non-Resident Bangladeshi
    "FOREIGN":   5,
}

# Dimension 3: PEP/IP status
PEP_IP_SCORES = {
    "NONE":           0,
    "PEP":            5,
    "PEP_FAMILY":     5,
    "IP_FLAG":        5,
    "IP_LOW":         1,
    "IP_MEDIUM":      3,
    "IP_HIGH":        5,
}

# Dimension 4: Product risk (Insurance)
PRODUCT_RISK_SCORES_INSURANCE = {
    "ORDINARY_LIFE":    1,
    "UNIVERSAL_LIFE":   2,
    "TERM":             3,
    "AH_RIDER":         3,
    "GROUP":            3,
    "HEALTH":           2,
}

# Dimension 4: Product risk (CMI)
PRODUCT_RISK_SCORES_CMI = {
    "BO_ACCOUNT":       2,
    "MARGIN_ACCOUNT":   3,
    "DISCRETIONARY":    3,
    "TRADING":          2,
}

# Dimension 5a: Business type (Annexure-1 lookup, abbreviated)
BUSINESS_TYPE_SCORES = {
    "AGRICULTURE":           1,
    "MANUFACTURING":         2,
    "RETAIL":                2,
    "WHOLESALE":             3,
    "IMPORT_EXPORT":         4,
    "MONEY_EXCHANGE":        5,
    "REAL_ESTATE":           4,
    "FINANCIAL_SERVICES":    4,
    "NGO":                   3,
    "GOVERNMENT":            1,
    "EDUCATION":             1,
    "HEALTHCARE":            2,
    "TECHNOLOGY":            2,
    "TRANSPORT":             3,
    "CONSTRUCTION":          3,
    "OTHER":                 3,
}

# Dimension 5b: Profession (Annexure-1 lookup, abbreviated)
PROFESSION_SCORES = {
    "GOVERNMENT_EMPLOYEE":   1,
    "MILITARY":              1,
    "TEACHER":               1,
    "DOCTOR":                2,
    "ENGINEER":              2,
    "BUSINESS_OWNER":        3,
    "FREELANCER":            3,
    "LAWYER":                3,
    "ACCOUNTANT":            2,
    "BANKER":                3,
    "POLITICIAN":            5,
    "JOURNALIST":            3,
    "STUDENT":               1,
    "HOUSEWIFE":             1,
    "RETIRED":               1,
    "UNEMPLOYED":            3,
    "OTHER":                 3,
}

# Dimension 6: Transactional risk (annual volume BDT)
def score_transaction_volume(annual_bdt: float) -> int:
    if annual_bdt < 1_000_000:
        return 1
    elif annual_bdt < 5_000_000:
        return 2
    elif annual_bdt < 50_000_000:
        return 3
    else:
        return 5

# Dimension 7: Transparency (source of funds)
TRANSPARENCY_SCORES = {
    "PROVIDED":     1,
    "NOT_PROVIDED": 5,
}

# ---------------------------------------------------------------------------
# Thresholds (BFIU Section 6.3)
# ---------------------------------------------------------------------------
HIGH_RISK_THRESHOLD    = 15   # Score >= 15 -> HIGH
MEDIUM_RISK_THRESHOLD  = 8    # Score 8-14 -> MEDIUM, below 8 -> LOW

REVIEW_FREQUENCY = {
    "LOW":    5,   # years
    "MEDIUM": 2,
    "HIGH":   1,
}

# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------
def calculate_risk_score(
    onboarding_channel:  str,
    residency:           str,
    pep_ip_status:       str,
    product_type:        str,
    business_type:       str,
    profession:          str,
    annual_income_bdt:   float,
    source_of_funds:     Optional[str],
    institution_type:    str = "INSURANCE",
    pep_flag:            bool = False,
    adverse_media:       bool = False,
) -> dict:
    """
    Calculate risk score across all 7 BFIU dimensions.
    Returns score, grade, EDD flag, dimension breakdown, review frequency.
    """
    scores = {}

    # Dimension 1: Onboarding channel
    scores["d1_onboarding_channel"] = ONBOARDING_CHANNEL_SCORES.get(
        onboarding_channel.upper(), 3
    )

    # Dimension 2: Geographic risk
    scores["d2_residency"] = RESIDENCY_SCORES.get(
        residency.upper(), 3
    )

    # Dimension 3: PEP/IP
    scores["d3_pep_ip"] = PEP_IP_SCORES.get(
        pep_ip_status.upper(), 0
    )

    # Dimension 4: Product risk
    if institution_type.upper() == "CMI":
        scores["d4_product"] = PRODUCT_RISK_SCORES_CMI.get(
            product_type.upper(), 2
        )
    else:
        scores["d4_product"] = PRODUCT_RISK_SCORES_INSURANCE.get(
            product_type.upper(), 2
        )

    # Dimension 5a: Business type
    scores["d5a_business"] = BUSINESS_TYPE_SCORES.get(
        business_type.upper(), 3
    )

    # Dimension 5b: Profession
    scores["d5b_profession"] = PROFESSION_SCORES.get(
        profession.upper(), 3
    )

    # Dimension 6: Transactional risk
    scores["d6_transaction"] = score_transaction_volume(annual_income_bdt)

    # Dimension 7: Transparency
    sof_status = "PROVIDED" if source_of_funds else "NOT_PROVIDED"
    scores["d7_transparency"] = TRANSPARENCY_SCORES.get(sof_status, 5)

    # Total score
    total = sum(scores.values())

    # Grade determination
    grade = _determine_grade(total, pep_flag, adverse_media)

    # EDD trigger
    edd_required = grade == "HIGH"

    # Review frequency
    review_years = REVIEW_FREQUENCY.get(grade, 2)

    return {
        "total_score":      total,
        "grade":            grade,
        "edd_required":     edd_required,
        "pep_override":     pep_flag,
        "adverse_media":    adverse_media,
        "review_years":     review_years,
        "dimension_scores": scores,
        "thresholds": {
            "high":   HIGH_RISK_THRESHOLD,
            "medium": MEDIUM_RISK_THRESHOLD,
        },
        "bfiu_ref": "BFIU Circular No. 29 - Section 6.3",
    }

def _determine_grade(score: int, pep_flag: bool, adverse_media: bool) -> str:
    """Determine risk grade with PEP/adverse media overrides."""
    # PEP/IP flag always overrides to HIGH regardless of score
    if pep_flag or adverse_media:
        return "HIGH"
    if score >= HIGH_RISK_THRESHOLD:
        return "HIGH"
    elif score >= MEDIUM_RISK_THRESHOLD:
        return "MEDIUM"
    return "LOW"

# ---------------------------------------------------------------------------
# EDD case creation helper
# ---------------------------------------------------------------------------
def create_edd_case(
    kyc_profile_id: str,
    risk_result: dict,
    institution_id: str,
) -> dict:
    """
    Create an EDD case record when HIGH risk is detected.
    In prod this writes to DB and notifies Chief AML/CFT Officer.
    """
    import uuid
    from datetime import datetime, timezone, timedelta

    case_id = str(uuid.uuid4())
    now     = datetime.now(timezone.utc)

    return {
        "case_id":          case_id,
        "kyc_profile_id":   kyc_profile_id,
        "institution_id":   institution_id,
        "risk_score":       risk_result["total_score"],
        "risk_grade":       risk_result["grade"],
        "pep_override":     risk_result["pep_override"],
        "adverse_media":    risk_result["adverse_media"],
        "status":           "PENDING",
        "sla_deadline":     (now + timedelta(days=30)).isoformat(),
        "created_at":       now.isoformat(),
        "bfiu_ref":         "BFIU Circular No. 29 - Section 4.3",
    }

# ---------------------------------------------------------------------------
# Re-scoring (triggered by lifecycle manager)
# ---------------------------------------------------------------------------
def rescore_profile(profile_data: dict) -> dict:
    """
    Re-score a KYC profile using stored fields.
    Used by M10 Lifecycle Manager on periodic review.
    """
    return calculate_risk_score(
        onboarding_channel = profile_data.get("onboarding_channel", "AGENCY"),
        residency          = profile_data.get("residency", "RESIDENT"),
        pep_ip_status      = profile_data.get("pep_ip_status", "NONE"),
        product_type       = profile_data.get("product_type", "ORDINARY_LIFE"),
        business_type      = profile_data.get("business_type", "OTHER"),
        profession         = profile_data.get("profession", "OTHER"),
        annual_income_bdt  = float(profile_data.get("monthly_income", 0) or 0) * 12,
        source_of_funds    = profile_data.get("source_of_funds"),
        institution_type   = profile_data.get("institution_type", "INSURANCE"),
        pep_flag           = profile_data.get("pep_flag", False),
        adverse_media      = profile_data.get("adverse_media", False),
    )
