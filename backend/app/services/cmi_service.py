"""
CMI / BO Account Service - M20
BFIU Circular No. 29 — Section 6.2 (Regular eKYC for Capital Markets)
2026 guidelines: Securities deposit threshold BDT 15,00,000

BO Account = Beneficiary Owner Account (CDBL system)
CMI = Capital Market Intermediaries

Flow:
  1. Customer completes eKYC (MATCHED verdict)
  2. CMI routes to BO account opening
  3. System checks 2026 threshold (BDT 15,00,000)
  4. CDBL stub called to register BO account
  5. Account number returned + notification sent
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── 2026 BFIU thresholds for Capital Markets ───────────────────────────────
CMI_THRESHOLDS_2026 = {
    "bo_simplified_max_deposit":    1_500_000,   # BDT 15,00,000
    "bo_regular_min_deposit":       1_500_001,
    "margin_account_min_equity":    500_000,     # BDT 5,00,000
    "portfolio_management_min":     1_000_000,   # BDT 10,00,000
    "edd_trigger_score":            15,
    "review_interval_high_years":   1,
    "review_interval_medium_years": 2,
    "review_interval_low_years":    5,
}

# ── BO Account product catalog ──────────────────────────────────────────────
BO_PRODUCTS = {
    "BO_INDIVIDUAL":     {
        "name":        "Individual BO Account",
        "description": "Standard beneficiary owner account for individual investors",
        "min_deposit":  0,
        "max_simplified": 1_500_000,
        "kyc_type":    "SIMPLIFIED",
        "cdbl_code":   "BO-IND",
    },
    "BO_JOINT":          {
        "name":        "Joint BO Account",
        "description": "Joint beneficiary owner account (max 2 holders)",
        "min_deposit":  0,
        "max_simplified": 1_500_000,
        "kyc_type":    "SIMPLIFIED",
        "cdbl_code":   "BO-JNT",
    },
    "BO_NRB":            {
        "name":        "NRB BO Account",
        "description": "Non-Resident Bangladeshi investor account",
        "min_deposit":  0,
        "max_simplified": 0,         # Always REGULAR for NRB
        "kyc_type":    "REGULAR",
        "cdbl_code":   "BO-NRB",
    },
    "MARGIN_ACCOUNT":    {
        "name":        "Margin Trading Account",
        "description": "Leveraged trading account — always REGULAR eKYC",
        "min_deposit":  500_000,
        "max_simplified": 0,         # Always REGULAR
        "kyc_type":    "REGULAR",
        "cdbl_code":   "MA-STD",
    },
    "PORTFOLIO_MGT":     {
        "name":        "Portfolio Management Account",
        "description": "Discretionary portfolio management",
        "min_deposit":  1_000_000,
        "max_simplified": 0,
        "kyc_type":    "REGULAR",
        "cdbl_code":   "PM-DIS",
    },
}

# ── CDBL stub (real integration requires CDBL API credentials) ──────────────
CDBL_MODE = "STUB"   # STUB | LIVE

def _cdbl_register_bo_account(
    investor_name:  str,
    nid_hash:       str,
    product_code:   str,
    kyc_session_id: str,
    institution_id: str,
) -> dict:
    """
    CDBL BO Account Registration Stub.
    In production: POST to CDBL API with signed JWT.
    Returns BO account number in format: 1201XXXXXXXXXX
    """
    if CDBL_MODE == "STUB":
        bo_number = f"1201{str(uuid.uuid4().int)[:10]}"
        return {
            "success":     True,
            "bo_number":   bo_number,
            "cdbl_ref":    f"CDBL-{str(uuid.uuid4())[:8].upper()}",
            "product_code": product_code,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "mode":        "STUB",
            "note":        "CDBL STUB — replace with live CDBL API credentials",
        }
    # LIVE mode placeholder
    raise NotImplementedError("CDBL LIVE integration requires API credentials")

# ── In-memory BO account store ──────────────────────────────────────────────
_bo_accounts: dict = {}   # keyed by bo_number
_session_index: dict = {} # session_id -> bo_number

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def open_bo_account(
    session_id:      str,
    kyc_verdict:     str,
    confidence:      float,
    full_name:       str,
    nid_hash:        str,
    mobile:          str,
    date_of_birth:   str,
    product_type:    str       = "BO_INDIVIDUAL",
    deposit_amount:  float     = 0.0,
    risk_grade:      str       = "LOW",
    risk_score:      int       = 0,
    pep_flag:        bool      = False,
    institution_id:  str       = "N/A",
    agent_id:        str       = "N/A",
    email:           Optional[str] = None,
    nominee_name:    Optional[str] = None,
    joint_holder:    Optional[str] = None,
) -> dict:
    """Open a CDBL BO account after successful eKYC."""

    # Validate verdict
    if kyc_verdict not in ("MATCHED", "REVIEW"):
        return {"success": False, "error": "BO account requires MATCHED or REVIEW verdict"}

    # Duplicate check
    if session_id in _session_index:
        existing = _bo_accounts[_session_index[session_id]]
        return {"success": True, "bo_account": existing, "already_exists": True}

    # Product validation
    if product_type not in BO_PRODUCTS:
        return {"success": False,
                "error": f"Unknown product_type. Must be one of: {list(BO_PRODUCTS)}"}

    product    = BO_PRODUCTS[product_type]
    kyc_type   = product["kyc_type"]

    # Override KYC type based on 2026 threshold
    if product_type in ("BO_INDIVIDUAL","BO_JOINT"):
        if deposit_amount > CMI_THRESHOLDS_2026["bo_simplified_max_deposit"]:
            kyc_type = "REGULAR"

    # PEP always REGULAR
    if pep_flag:
        kyc_type = "REGULAR"

    # Determine auto-approval
    auto_approved = (
        kyc_verdict == "MATCHED"
        and risk_grade == "LOW"
        and not pep_flag
        and deposit_amount <= CMI_THRESHOLDS_2026["bo_simplified_max_deposit"]
    )

    # CDBL registration
    cdbl_result = _cdbl_register_bo_account(
        investor_name  = full_name,
        nid_hash       = nid_hash,
        product_code   = product["cdbl_code"],
        kyc_session_id = session_id,
        institution_id = institution_id,
    )

    if not cdbl_result["success"]:
        return {"success": False, "error": "CDBL registration failed", "cdbl": cdbl_result}

    bo_number = cdbl_result["bo_number"]
    status    = "ACTIVE" if auto_approved else "PENDING_REVIEW"

    account = {
        "bo_number":       bo_number,
        "cdbl_ref":        cdbl_result["cdbl_ref"],
        "session_id":      session_id,
        "full_name":       full_name,
        "mobile":          mobile,
        "email":           email,
        "date_of_birth":   date_of_birth,
        "product_type":    product_type,
        "product_name":    product["name"],
        "cdbl_code":       product["cdbl_code"],
        "deposit_amount":  deposit_amount,
        "kyc_type":        kyc_type,
        "kyc_verdict":     kyc_verdict,
        "confidence":      confidence,
        "risk_grade":      risk_grade,
        "risk_score":      risk_score,
        "pep_flag":        pep_flag,
        "status":          status,
        "auto_approved":   auto_approved,
        "institution_id":  institution_id,
        "agent_id":        agent_id,
        "nominee_name":    nominee_name,
        "joint_holder":    joint_holder,
        "threshold_applied": CMI_THRESHOLDS_2026["bo_simplified_max_deposit"],
        "threshold_2026":  True,
        "created_at":      _now(),
        "bfiu_ref":        "BFIU Circular No. 29 — Section 6.2 (2026)",
    }

    _bo_accounts[bo_number]     = account
    _session_index[session_id]  = bo_number
    return {"success": True, "bo_account": account, "already_exists": False}


def get_bo_account(bo_number: str) -> Optional[dict]:
    return _bo_accounts.get(bo_number)


def get_bo_by_session(session_id: str) -> Optional[dict]:
    bn = _session_index.get(session_id)
    return _bo_accounts.get(bn) if bn else None


def list_bo_accounts(status: Optional[str] = None, limit: int = 100) -> list:
    items = list(_bo_accounts.values())
    if status:
        items = [a for a in items if a["status"] == status]
    return items[-limit:]


def get_threshold_info() -> dict:
    return {
        "thresholds_2026":    CMI_THRESHOLDS_2026,
        "products":           BO_PRODUCTS,
        "simplified_max_bdt": CMI_THRESHOLDS_2026["bo_simplified_max_deposit"],
        "regular_min_bdt":    CMI_THRESHOLDS_2026["bo_regular_min_deposit"],
        "bfiu_ref":           "BFIU Circular No. 29 — Section 6.2 (2026)",
        "deadline":           "December 31, 2026",
    }
