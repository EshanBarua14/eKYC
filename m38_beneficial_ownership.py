"""
M38 — Beneficial Ownership
BFIU Circular No. 29 §4.2 + Blueprint §5.1
Mandatory for Regular e-KYC.

Routes:
  POST   /api/v1/kyc/beneficial-owner          — add BO to a profile
  GET    /api/v1/kyc/beneficial-owner/{session_id} — list BOs for session
  DELETE /api/v1/kyc/beneficial-owner/{bo_id}  — remove BO
  POST   /api/v1/kyc/beneficial-owner/declaration — submit no-BO or all-disclosed declaration
  GET    /api/v1/kyc/beneficial-owner/compliance-status/{session_id} — gate check
"""
# ── Paste into: app/api/v1/routes/beneficial_owner.py ────────────────────

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import KYCProfile, AuditLog
from app.core.security import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

router   = APIRouter(prefix="/kyc", tags=["Beneficial Ownership — M38"])
security = HTTPBearer()


def _now():
    return datetime.now(timezone.utc)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def _audit(db: Session, event: str, entity_id: str, session_id: str,
           actor: dict, detail: dict, bfiu_ref: str = "BFIU Circular No. 29 §4.2"):
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        event_type=event,
        entity_type="beneficial_owner",
        entity_id=entity_id,
        actor_id=actor.get("user_id") or actor.get("sub"),
        actor_role=actor.get("role"),
        session_id=session_id,
        after_state=detail,
        bfiu_ref=bfiu_ref,
        retention_until=datetime(2031, 12, 31, tzinfo=timezone.utc),
        timestamp=_now(),
    ))


# ══════════════════════════════════════════════════════════════════════════
# SQLAlchemy model — add to app/db/models.py
# ══════════════════════════════════════════════════════════════════════════
# COPY THIS BLOCK INTO app/db/models.py after the KYCProfile class:
"""
class BeneficialOwner(Base):
    __tablename__ = "beneficial_owners"
    id                  = Column(String(36),  primary_key=True, index=True)
    session_id          = Column(String(128), ForeignKey("kyc_profiles.session_id"),
                                 nullable=False, index=True)
    full_name           = Column(String(255), nullable=False)
    nid_number          = Column(String(32),  nullable=True)
    date_of_birth       = Column(String(20),  nullable=True)
    nationality         = Column(String(64),  default="Bangladeshi")
    ownership_type      = Column(String(30),  nullable=False, default="direct")
    ownership_pct       = Column(Float,       nullable=True)
    control_mechanism   = Column(Text,        nullable=True)
    relationship        = Column(String(200), nullable=True)
    source_of_funds     = Column(Text,        nullable=True)
    is_pep              = Column(Boolean,     default=False)
    is_sanctioned       = Column(Boolean,     default=False)
    unscr_checked       = Column(Boolean,     default=False)
    unscr_checked_at    = Column(DateTime,    nullable=True)
    edd_required        = Column(Boolean,     default=False)
    verification_status = Column(String(20),  default="PENDING")
    identified_by       = Column(String(128), nullable=True)
    bfiu_ref            = Column(String(64),  default="BFIU Circular No. 29 §4.2")
    created_at          = Column(DateTime,    default=_now)
    updated_at          = Column(DateTime,    default=_now, onupdate=_now)


class BODeclaration(Base):
    __tablename__ = "bo_declarations"
    id                   = Column(String(36),  primary_key=True, index=True)
    session_id           = Column(String(128), ForeignKey("kyc_profiles.session_id"),
                                  unique=True, nullable=False, index=True)
    has_beneficial_owner = Column(Boolean,     nullable=False)
    declaration_text     = Column(Text,        nullable=True)
    declared_by          = Column(String(128), nullable=True)
    declaration_ip       = Column(String(45),  nullable=True)
    checker_reviewed     = Column(Boolean,     default=False)
    bfiu_ref             = Column(String(64),  default="BFIU Circular No. 29 §4.2")
    created_at           = Column(DateTime,    default=_now)
"""

# ══════════════════════════════════════════════════════════════════════════
# Pydantic schemas
# ══════════════════════════════════════════════════════════════════════════

class BOCreateRequest(BaseModel):
    session_id:         str
    full_name:          str
    nid_number:         Optional[str]   = None
    date_of_birth:      Optional[str]   = None
    nationality:        str             = "Bangladeshi"
    ownership_type:     str             = "direct"   # direct|indirect|senior_manager|other
    ownership_pct:      Optional[float] = None
    control_mechanism:  Optional[str]   = None
    relationship:       Optional[str]   = None
    source_of_funds:    Optional[str]   = None

    @validator("ownership_type")
    def valid_type(cls, v):
        allowed = {"direct", "indirect", "senior_manager", "other"}
        if v not in allowed:
            raise ValueError(f"ownership_type must be one of {sorted(allowed)}")
        return v

    @validator("ownership_pct")
    def valid_pct(cls, v):
        if v is not None and not (0 < v <= 100):
            raise ValueError("ownership_pct must be between 0 and 100")
        return v


class BODeclarationRequest(BaseModel):
    session_id:          str
    has_beneficial_owner: bool
    declaration_text:    Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════════

@router.post("/beneficial-owner", status_code=201,
             summary="Add beneficial owner — BFIU §4.2 Regular e-KYC",
             operation_id="bo_create")
def create_beneficial_owner(
    req: BOCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_user),
):
    # 1. Profile must exist
    profile = db.query(KYCProfile).filter_by(session_id=req.session_id).first()
    if not profile:
        raise HTTPException(404, f"KYC profile not found for session {req.session_id!r}")

    # 2. BO only required for Regular e-KYC (but allow on any type — don't block)
    from app.db.models import BeneficialOwner
    bo = BeneficialOwner(
        id=str(uuid.uuid4()),
        session_id=req.session_id,
        full_name=req.full_name,
        nid_number=req.nid_number,
        date_of_birth=req.date_of_birth,
        nationality=req.nationality,
        ownership_type=req.ownership_type,
        ownership_pct=req.ownership_pct,
        control_mechanism=req.control_mechanism,
        relationship=req.relationship,
        source_of_funds=req.source_of_funds,
        identified_by=actor.get("user_id") or actor.get("sub"),
        verification_status="PENDING",
    )
    db.add(bo)

    # 3. Run inline UNSCR screen (sync — async Celery optional later)
    try:
        from app.services.screening_service import screen_unscr
        result = screen_unscr(req.full_name)
        bo.is_sanctioned = result.get("matched", False)
        bo.unscr_checked = True
        bo.unscr_checked_at = _now()
        if bo.is_sanctioned:
            bo.edd_required = True
            bo.verification_status = "EDD_REQUIRED"
        else:
            bo.verification_status = "VERIFIED"
    except Exception:
        # Screening failure must not block BO creation — log and continue
        bo.verification_status = "PENDING"

    # 4. PEP check via existing screening service
    try:
        from app.services.screening_service import screen_pep
        pep_result = screen_pep(req.full_name)
        bo.is_pep = pep_result.get("matched", False)
        if bo.is_pep:
            bo.edd_required = True
            bo.verification_status = "EDD_REQUIRED"
            # Propagate EDD to parent profile
            profile.edd_required = True
            profile.pep_flag = True
    except Exception:
        pass

    # 5. Audit
    _audit(db, "BO_IDENTIFIED", bo.id, req.session_id, actor, {
        "full_name": req.full_name,
        "ownership_type": req.ownership_type,
        "is_pep": bo.is_pep,
        "is_sanctioned": bo.is_sanctioned,
        "edd_required": bo.edd_required,
    })

    db.commit()
    db.refresh(bo)

    return {
        "beneficial_owner": {
            "id": bo.id,
            "session_id": bo.session_id,
            "full_name": bo.full_name,
            "ownership_type": bo.ownership_type,
            "ownership_pct": bo.ownership_pct,
            "is_pep": bo.is_pep,
            "is_sanctioned": bo.is_sanctioned,
            "unscr_checked": bo.unscr_checked,
            "edd_required": bo.edd_required,
            "verification_status": bo.verification_status,
            "created_at": bo.created_at.isoformat() if bo.created_at else None,
        },
        "bfiu_ref": "BFIU Circular No. 29 §4.2",
    }


@router.get("/beneficial-owner/{session_id}",
            summary="List beneficial owners for a session",
            operation_id="bo_list")
def list_beneficial_owners(
    session_id: str,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_user),
):
    from app.db.models import BeneficialOwner
    bos = db.query(BeneficialOwner).filter_by(session_id=session_id).all()
    return {
        "session_id": session_id,
        "count": len(bos),
        "beneficial_owners": [
            {
                "id": b.id,
                "full_name": b.full_name,
                "ownership_type": b.ownership_type,
                "ownership_pct": b.ownership_pct,
                "is_pep": b.is_pep,
                "is_sanctioned": b.is_sanctioned,
                "edd_required": b.edd_required,
                "verification_status": b.verification_status,
                "unscr_checked": b.unscr_checked,
            }
            for b in bos
        ],
        "bfiu_ref": "BFIU Circular No. 29 §4.2",
    }


@router.delete("/beneficial-owner/record/{bo_id}",
               summary="Remove a beneficial owner record",
               operation_id="bo_delete")
def delete_beneficial_owner(
    bo_id: str,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_user),
):
    from app.db.models import BeneficialOwner
    bo = db.query(BeneficialOwner).filter_by(id=bo_id).first()
    if not bo:
        raise HTTPException(404, f"Beneficial owner {bo_id!r} not found")

    _audit(db, "BO_REMOVED", bo_id, bo.session_id, actor,
           {"full_name": bo.full_name, "reason": "manual removal"})
    db.delete(bo)
    db.commit()
    return {"deleted": True, "bo_id": bo_id}


@router.post("/beneficial-owner/declaration",
             summary="Submit BO declaration — required before Regular e-KYC finalisation",
             operation_id="bo_declaration",
             status_code=201)
def submit_bo_declaration(
    req: BODeclarationRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_user),
):
    from app.db.models import BeneficialOwner, BODeclaration

    profile = db.query(KYCProfile).filter_by(session_id=req.session_id).first()
    if not profile:
        raise HTTPException(404, f"KYC profile not found for session {req.session_id!r}")

    bos = db.query(BeneficialOwner).filter_by(session_id=req.session_id).all()

    # Consistency checks
    if req.has_beneficial_owner and not bos:
        raise HTTPException(400,
            "has_beneficial_owner=true but no BO records exist. "
            "Add at least one via POST /kyc/beneficial-owner first.")

    if not req.has_beneficial_owner and bos:
        raise HTTPException(400,
            "has_beneficial_owner=false but BO records exist. "
            "Remove them first or set has_beneficial_owner=true.")

    # Upsert declaration
    existing = db.query(BODeclaration).filter_by(session_id=req.session_id).first()
    if existing:
        existing.has_beneficial_owner = req.has_beneficial_owner
        existing.declaration_text = req.declaration_text
        existing.declared_by = actor.get("user_id") or actor.get("sub")
        existing.declaration_ip = request.client.host if request.client else None
        decl = existing
        created = False
    else:
        decl = BODeclaration(
            id=str(uuid.uuid4()),
            session_id=req.session_id,
            has_beneficial_owner=req.has_beneficial_owner,
            declaration_text=req.declaration_text or (
                "I confirm no beneficial owner exists." if not req.has_beneficial_owner
                else "All beneficial owners have been disclosed."
            ),
            declared_by=actor.get("user_id") or actor.get("sub"),
            declaration_ip=request.client.host if request.client else None,
        )
        db.add(decl)
        created = True

    _audit(db, "BO_DECLARATION_SUBMITTED", decl.id, req.session_id, actor, {
        "has_beneficial_owner": req.has_beneficial_owner,
        "bo_count": len(bos),
    })
    db.commit()

    return {
        "declaration_id": decl.id,
        "session_id": req.session_id,
        "has_beneficial_owner": decl.has_beneficial_owner,
        "declaration_text": decl.declaration_text,
        "created": created,
        "bfiu_ref": "BFIU Circular No. 29 §4.2",
    }


@router.get("/beneficial-owner/compliance-status/{session_id}",
            summary="Check if BO requirement is satisfied for Regular e-KYC sign-off",
            operation_id="bo_compliance_status")
def bo_compliance_status(
    session_id: str,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_user),
):
    from app.db.models import BeneficialOwner, BODeclaration

    profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
    if not profile:
        raise HTTPException(404, f"KYC profile not found for session {session_id!r}")

    bos = db.query(BeneficialOwner).filter_by(session_id=session_id).all()
    decl = db.query(BODeclaration).filter_by(session_id=session_id).first()

    pending_screen  = [b for b in bos if not b.unscr_checked]
    edd_incomplete  = [b for b in bos if b.edd_required and b.verification_status != "VERIFIED"]

    is_compliant = (
        decl is not None
        and len(pending_screen) == 0
        and len(edd_incomplete) == 0
    )

    blockers = []
    if not decl:
        blockers.append("BO declaration not submitted — POST /kyc/beneficial-owner/declaration")
    if pending_screen:
        blockers.append(f"{len(pending_screen)} BO(s) awaiting UNSCR screening")
    if edd_incomplete:
        blockers.append(f"{len(edd_incomplete)} BO(s) require EDD completion")

    return {
        "session_id":           session_id,
        "kyc_type":             profile.kyc_type,
        "declaration_submitted": decl is not None,
        "beneficial_owners":    len(bos),
        "pending_screening":    len(pending_screen),
        "edd_required_count":   len(edd_incomplete),
        "bo_check_complete":    is_compliant,
        "blockers":             blockers,
        "bfiu_ref":             "BFIU Circular No. 29 §4.2",
    }
