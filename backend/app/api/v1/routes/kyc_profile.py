"""
KYC Profile Route — M6
BFIU Circular No. 29 — Section 6.1 (Simplified) and 6.2 (Regular)

POST /api/v1/kyc/profile  — create profile from verified session
GET  /api/v1/kyc/profile/{session_id} — retrieve profile
GET  /api/v1/kyc/profiles — list all profiles (admin)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.db.database import get_db
from app.db.models import KYCProfile
from app.services import file_storage
from app.services.kyc_threshold import assign_kyc_type, calculate_risk_score

router = APIRouter(prefix="/kyc", tags=["KYC Profile"])


# ── Request schema ─────────────────────────────────────────────────────────

class KYCProfileRequest(BaseModel):
    # Required — from verified session
    session_id:       str
    verdict:          str        # must be MATCHED or REVIEW
    confidence:       float

    # Institution context
    institution_type: str = "INSURANCE_LIFE"
    product_type:     Optional[str]   = None
    product_amount:   Optional[float] = None

    # Personal info (BFIU §6.1 minimum)
    full_name:        str
    date_of_birth:    str
    mobile:           str
    fathers_name:     Optional[str]   = None
    mothers_name:     Optional[str]   = None
    spouse_name:      Optional[str]   = None
    gender:           Optional[str]   = None
    email:            Optional[str]   = None
    present_address:  Optional[str]   = None
    permanent_address: Optional[str]  = None
    nationality:      str = "Bangladeshi"
    profession:       Optional[str]   = None
    monthly_income:   Optional[float] = None
    source_of_funds:  Optional[str]   = None

    # Regular eKYC extras
    tin:              Optional[str]   = None
    account_number:   Optional[str]   = None

    # Nominee
    nominee_name:     Optional[str]   = None
    nominee_relation: Optional[str]   = None

    # Compliance
    pep_flag:         bool = False
    unscr_checked:    bool = False


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/profile", summary="Create KYC profile from verified session")
def create_profile(req: KYCProfileRequest, db: Session = Depends(get_db)):

    # Only allow MATCHED or REVIEW verdicts
    if req.verdict not in ("MATCHED", "REVIEW"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create KYC profile for verdict '{req.verdict}'. Must be MATCHED or REVIEW."
        )

    # Prevent duplicate
    existing = db.query(KYCProfile).filter_by(session_id=req.session_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Profile for session '{req.session_id}' already exists.")

    # Auto-assign KYC type
    kyc_type = assign_kyc_type(req.institution_type, req.product_type, req.product_amount)

    # Risk scoring
    risk_score, risk_grade, edd_required = calculate_risk_score(req.model_dump())

    # EDD override for REVIEW verdict
    if req.verdict == "REVIEW":
        edd_required = True
        risk_grade   = max(risk_grade, "MEDIUM")

    profile = KYCProfile(
        session_id        = req.session_id,
        verdict           = req.verdict,
        confidence        = req.confidence,
        institution_type  = req.institution_type,
        product_type      = req.product_type,
        product_amount    = req.product_amount,
        kyc_type          = kyc_type,
        status            = "EDD_REQUIRED" if edd_required else "PENDING",
        full_name         = req.full_name,
        fathers_name      = req.fathers_name,
        mothers_name      = req.mothers_name,
        spouse_name       = req.spouse_name,
        date_of_birth     = req.date_of_birth,
        gender            = req.gender,
        mobile            = req.mobile,
        email             = req.email,
        present_address   = req.present_address,
        permanent_address = req.permanent_address,
        nationality       = req.nationality,
        profession        = req.profession,
        monthly_income    = req.monthly_income,
        source_of_funds   = req.source_of_funds,
        tin               = req.tin,
        account_number    = req.account_number,
        nominee_name      = req.nominee_name,
        nominee_relation  = req.nominee_relation,
        pep_flag          = req.pep_flag,
        unscr_checked     = req.unscr_checked,
        source_of_funds_verified = bool(req.source_of_funds),
        edd_required      = edd_required,
        risk_score        = risk_score,
        risk_grade        = risk_grade,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "profile_id":    profile.id,
        "session_id":    profile.session_id,
        "kyc_type":      profile.kyc_type,
        "status":        profile.status,
        "risk_grade":    profile.risk_grade,
        "risk_score":    profile.risk_score,
        "edd_required":  profile.edd_required,
        "full_name":     profile.full_name,
        "created_at":    profile.created_at.isoformat(),
        "bfiu_ref":      profile.bfiu_ref,
        "thresholds_applied": {
            "institution_type": profile.institution_type,
            "product_type":     profile.product_type,
            "product_amount":   profile.product_amount,
            "kyc_type_reason":  f"{profile.kyc_type} — BFIU Circular No. 29 §6.1",
        },
    }


@router.get("/profile/{session_id}", summary="Get KYC profile by session ID")
def get_profile(session_id: str, db: Session = Depends(get_db)):
    profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile found for session '{session_id}'")
    return _serialize(profile)


@router.get("/profiles", summary="List all KYC profiles (admin)")
def list_profiles(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    profiles = db.query(KYCProfile).offset(skip).limit(limit).all()
    return {
        "total":    db.query(KYCProfile).count(),
        "profiles": [_serialize(p) for p in profiles],
    }


@router.patch("/profile/{session_id}/approve", summary="Approve KYC profile (checker)")
def approve_profile(session_id: str, db: Session = Depends(get_db)):
    profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.edd_required and not profile.unscr_checked:
        raise HTTPException(status_code=400, detail="EDD required — complete UNSCR check before approval")
    profile.status     = "APPROVED"
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"session_id": session_id, "status": "APPROVED", "bfiu_ref": profile.bfiu_ref}


@router.patch("/profile/{session_id}/reject", summary="Reject KYC profile")
def reject_profile(session_id: str, db: Session = Depends(get_db)):
    profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.status     = "REJECTED"
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"session_id": session_id, "status": "REJECTED"}


def _serialize(p: KYCProfile) -> dict:
    return {
        "profile_id":       p.id,
        "session_id":       p.session_id,
        "verdict":          p.verdict,
        "confidence":       p.confidence,
        "kyc_type":         p.kyc_type,
        "status":           p.status,
        "institution_type": p.institution_type,
        "product_type":     p.product_type,
        "product_amount":   p.product_amount,
        "full_name":        p.full_name,
        "date_of_birth":    p.date_of_birth,
        "mobile":           p.mobile,
        "gender":           p.gender,
        "nationality":      p.nationality,
        "profession":       p.profession,
        "source_of_funds":  p.source_of_funds,
        "nominee_name":     p.nominee_name,
        "pep_flag":         p.pep_flag,
        "unscr_checked":    p.unscr_checked,
        "edd_required":     p.edd_required,
        "risk_score":       p.risk_score,
        "risk_grade":       p.risk_grade,
        "status":           p.status,
        "created_at":       p.created_at.isoformat(),
        "bfiu_ref":         p.bfiu_ref,
    }
