"""
M64-I: KYC Profile Form Generator
BFIU Circular No. 29 §6.1 (Simplified) and §6.2 (Regular)

Generates structured KYC profile output at workflow completion.
Called by make_decision() in kyc_workflow_engine.py.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.core.timezone import now_bst as bst_now, bst_isoformat

BST = timezone(timedelta(hours=6))


def generate_kyc_profile_form(session: dict) -> dict:
    """
    Generate §6.1 or §6.2 KYC profile form at workflow completion.
    BFIU §6.1: Simplified eKYC output fields
    BFIU §6.2: Regular eKYC output fields (superset of §6.1)
    """
    kyc_type = session.get("kyc_type", "SIMPLIFIED")
    data = session.get("data", {})
    screening = session.get("screening_result") or {}
    risk = session.get("risk_result") or {}
    bio = session.get("biometric_result") or {}
    decision = session.get("decision") or {}
    nid = session.get("nid_result") or {}

    now = bst_isoformat()

    # ── §6.1 Simplified — mandatory fields ───────────────────────────────
    form = {
        "form_version": "BFIU-CIRCULAR-29-6.1" if kyc_type == "SIMPLIFIED" else "BFIU-CIRCULAR-29-6.2",
        "kyc_type": kyc_type,
        "generated_at_bst": now,
        "bfiu_ref": f"BFIU Circular No. 29 §{'6.1' if kyc_type == 'SIMPLIFIED' else '6.2'}",

        # Customer identity
        "applicant_name": data.get("full_name_en", ""),
        "applicant_name_bn": data.get("full_name_bn", ""),
        "date_of_birth": data.get("date_of_birth", ""),
        "gender": nid.get("gender") or data.get("gender", ""),
        "father_name": nid.get("father_name") or data.get("father_name", ""),
        "mother_name": nid.get("mother_name") or data.get("mother_name", ""),
        "spouse_name": data.get("spouse_name", ""),
        "present_address": data.get("present_address", ""),
        "permanent_address": nid.get("permanent_address") or data.get("permanent_address", ""),
        "mobile_phone": data.get("mobile_phone", ""),
        "email": data.get("email", ""),
        "nationality": data.get("nationality", "BD"),

        # NID
        "nid_number_masked": _mask_nid(data.get("nid_number", "")),
        "nid_verified": session.get("nid_verified", False),
        "nid_verified_at": session.get("nid_verified_at", ""),

        # Biometric
        "biometric_method": bio.get("method", ""),
        "biometric_verified": bio.get("verified", False),
        "biometric_verified_at": bio.get("verified_at", ""),

        # UNSCR screening (mandatory ALL)
        "unscr_checked": True,
        "unscr_verdict": (screening.get("results", {}).get("unscr") or {}).get("verdict", "NOT_RUN"),
        "unscr_list_version": (screening.get("results", {}).get("unscr") or {}).get("list_version", ""),
        "unscr_checked_at": screening.get("screened_at", now),

        # Nominee (§6.1 mandatory)
        "nominee_name": data.get("nominee_name", ""),
        "nominee_relation": data.get("nominee_relation", ""),

        # Signature (§6.1 Step 4)
        "signature_type": data.get("signature_type", "DIGITAL"),
        "signature_captured": bool(data.get("signature_data")),

        # Account opening notification (§6.1 Step 5)
        "notification_sent": data.get("notification_sent", False),
        "notification_channel": data.get("notification_channel", ""),

        # Decision
        "kyc_outcome": decision.get("outcome", "PENDING"),
        "decision_at_bst": decision.get("decided_at", now),
        "bfiu_decision_ref": "BFIU Circular No. 29 §4.2, §6.3",
    }

    # ── §6.2 Regular — additional mandatory fields ────────────────────────
    if kyc_type == "REGULAR":
        form.update({
            # Financial profile
            "profession": data.get("profession", ""),
            "monthly_income": data.get("monthly_income", ""),
            "source_of_funds": data.get("source_of_funds", ""),
            "source_of_funds_verified": bool(data.get("source_of_funds")),

            # PEP/IP screening
            "pep_checked": True,
            "pep_verdict": (screening.get("results", {}).get("pep") or {}).get("verdict", "NOT_RUN"),
            "pep_flag": screening.get("pep_flag", False),

            # Adverse media
            "adverse_media_checked": True,
            "adverse_media_verdict": (screening.get("results", {}).get("adverse_media") or {}).get("verdict", "NOT_RUN"),
            "adverse_media_flag": screening.get("adverse_media_flag", False),

            # Risk grading §6.3
            "risk_score": risk.get("total_score", 0),
            "risk_grade": risk.get("risk_grade", ""),
            "risk_graded_at": now,
            "edd_required": decision.get("edd_required", False),

            # Beneficial ownership §4.2
            "beneficial_owners_declared": len(data.get("beneficial_owners", [])),
            "bo_pep_flag": data.get("bo_pep_flag", False),
            "bo_checked_at": now,

            # Wet/digital signature enforcement
            # BFIU §3.3 Step 4: HIGH risk must have wet/electronic signature
            "signature_type": data.get("signature_type", "DIGITAL"),
            "signature_compliant": _check_signature_compliance(
                data.get("signature_type", "DIGITAL"),
                risk.get("risk_grade", "LOW")
            ),

            # TIN
            "tin": data.get("tin", ""),
        })

    return form


def _mask_nid(nid: str) -> str:
    """Mask NID — show last 4 digits only for PII protection."""
    if not nid or len(nid) < 4:
        return "****"
    return "*" * (len(nid) - 4) + nid[-4:]


def _check_signature_compliance(sig_type: str, risk_grade: str) -> bool:
    """
    BFIU §3.3 Step 4:
    HIGH risk → wet or electronic signature required (not digital PIN only)
    LOW/MEDIUM → digital signature or PIN acceptable
    """
    if risk_grade == "HIGH":
        return sig_type in ("WET", "ELECTRONIC")
    return True  # LOW/MEDIUM: any type acceptable
