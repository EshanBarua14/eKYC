"""
M73: Source of Funds Verification Logic
BFIU Circular No. 29 §4.2 — Regular eKYC CDD requirement

Rules:
- source_of_funds field required for Regular eKYC
- Must be from allowed list or OTHER with explanation
- High-risk sources trigger additional documentation flag
- Document upload flag set for sources requiring proof
"""
from __future__ import annotations

ALLOWED_SOURCES = {
    "SALARY",           # Regular employment
    "BUSINESS_INCOME",  # Business owner
    "INVESTMENT",       # Investment returns
    "RENTAL_INCOME",    # Property rental
    "PENSION",          # Retirement pension
    "REMITTANCE",       # Foreign remittance
    "INHERITANCE",      # Inheritance
    "SAVINGS",          # Personal savings
    "AGRICULTURE",      # Agricultural income
    "FREELANCE",        # Freelance/consultancy
    "GOVERNMENT_GRANT", # Government benefits
    "OTHER",            # Other — requires explanation
}

# Sources requiring document upload (BFIU §4.2 CDD)
HIGH_SCRUTINY_SOURCES = {
    "REMITTANCE",       # Foreign source — scrutinise
    "INHERITANCE",      # Estate documents needed
    "INVESTMENT",       # Investment records needed
    "OTHER",            # Unknown — mandatory explanation
}


class SourceOfFundsValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_source_of_funds(
    source: str | None,
    explanation: str | None = None,
    kyc_type: str = "REGULAR",
    annual_income_bdt: float = 0,
) -> dict:
    """
    Validate source of funds for Regular eKYC (BFIU §4.2).
    Returns validation result with document_required flag.
    """
    if kyc_type != "REGULAR":
        return {"validated": True, "required": False, "bfiu_ref": "BFIU §4.2 — Simplified eKYC"}

    if not source or not source.strip():
        raise SourceOfFundsValidationError(
            "source_of_funds",
            "Source of funds is required for Regular eKYC (BFIU §4.2)"
        )

    source_upper = source.strip().upper()

    if source_upper not in ALLOWED_SOURCES:
        raise SourceOfFundsValidationError(
            "source_of_funds",
            f"Invalid source '{source}'. Allowed: {sorted(ALLOWED_SOURCES)}"
        )

    if source_upper == "OTHER" and not explanation:
        raise SourceOfFundsValidationError(
            "source_of_funds_explanation",
            "Explanation required when source is OTHER (BFIU §4.2)"
        )

    document_required = source_upper in HIGH_SCRUTINY_SOURCES
    risk_flag = source_upper in HIGH_SCRUTINY_SOURCES

    # High income without clear source — flag for review
    if annual_income_bdt > 5_000_000 and source_upper not in {"BUSINESS_INCOME", "INVESTMENT", "SALARY"}:
        risk_flag = True
        document_required = True

    return {
        "validated": True,
        "source": source_upper,
        "explanation": explanation,
        "document_required": document_required,
        "risk_flag": risk_flag,
        "high_scrutiny": source_upper in HIGH_SCRUTINY_SOURCES,
        "bfiu_ref": "BFIU Circular No. 29 §4.2 — CDD source of funds verification",
    }


def validate_sof_from_data(data: dict, kyc_type: str = "REGULAR") -> dict | None:
    """Validate source of funds from session data dict."""
    if kyc_type != "REGULAR":
        return None

    source = data.get("source_of_funds", "").strip()
    explanation = data.get("source_of_funds_explanation", "")
    monthly_income = float(data.get("monthly_income", 0) or 0)

    if not source:
        return {
            "validated": False,
            "warning": "Source of funds not provided. Required for Regular eKYC (BFIU §4.2).",
            "bfiu_ref": "BFIU Circular No. 29 §4.2",
        }

    return validate_source_of_funds(
        source=source,
        explanation=explanation or None,
        kyc_type=kyc_type,
        annual_income_bdt=monthly_income * 12,
    )
