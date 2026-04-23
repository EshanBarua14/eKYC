"""M38 - Beneficial Ownership - BFIU Circular No. 29 s4.2"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.middleware.tenant_db import get_tenant_db
from app.db.models import KYCProfile, AuditLog
from app.core.security import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

router   = APIRouter(prefix="/kyc", tags=["Beneficial Ownership"])
security = HTTPBearer()

def _now(): return datetime.now(timezone.utc)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try: return decode_token(credentials.credentials)
    except JWTError as e: raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

def _audit(db, event, entity_id, session_id, actor, detail):
    db.add(AuditLog(
        id=str(uuid.uuid4()), event_type=event, entity_type="beneficial_owner",
        entity_id=entity_id, actor_id=actor.get("user_id") or actor.get("sub"),
        actor_role=actor.get("role"), session_id=session_id, after_state=detail,
        bfiu_ref="BFIU Circular No. 29 s4.2",
        retention_until=datetime(2031,12,31,tzinfo=timezone.utc), timestamp=_now(),
    ))

class BOCreateRequest(BaseModel):
    session_id: str
    full_name: str
    nid_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: str = "Bangladeshi"
    ownership_type: str = "direct"
    ownership_pct: Optional[float] = None
    control_mechanism: Optional[str] = None
    relationship: Optional[str] = None
    source_of_funds: Optional[str] = None

    @validator("ownership_type")
    def valid_type(cls, v):
        if v not in {"direct","indirect","senior_manager","other"}:
            raise ValueError("ownership_type must be direct|indirect|senior_manager|other")
        return v

class BODeclarationRequest(BaseModel):
    session_id: str
    has_beneficial_owner: bool
    declaration_text: Optional[str] = None

@router.post("/beneficial-owner", status_code=201, operation_id="bo_create")
def create_beneficial_owner(req: BOCreateRequest, request: Request,
    db: Session = Depends(get_tenant_db), actor: dict = Depends(get_current_user)):
    from app.db.models import BeneficialOwner
    profile = db.query(KYCProfile).filter_by(session_id=req.session_id).first()
    if not profile: raise HTTPException(404, f"KYC profile not found: {req.session_id!r}")
    bo = BeneficialOwner(
        id=str(uuid.uuid4()), session_id=req.session_id, full_name=req.full_name,
        nid_number=req.nid_number, date_of_birth=req.date_of_birth,
        nationality=req.nationality, ownership_type=req.ownership_type,
        ownership_pct=req.ownership_pct, control_mechanism=req.control_mechanism,
        relationship=req.relationship, source_of_funds=req.source_of_funds,
        identified_by=actor.get("user_id") or actor.get("sub"), verification_status="PENDING",
    )
    db.add(bo)
    try:
        from app.services.screening_service import screen_unscr, screen_pep
        r = screen_unscr(req.full_name)
        bo.is_sanctioned = r.get("matched", False)
        bo.unscr_checked = True; bo.unscr_checked_at = _now()
        p = screen_pep(req.full_name)
        bo.is_pep = p.get("matched", False)
        if bo.is_sanctioned or bo.is_pep:
            bo.edd_required = True; bo.verification_status = "EDD_REQUIRED"
            profile.edd_required = True
            if bo.is_pep: profile.pep_flag = True
        else:
            bo.verification_status = "VERIFIED"
    except Exception:
        pass
    _audit(db, "BO_IDENTIFIED", bo.id, req.session_id, actor,
           {"full_name": req.full_name, "ownership_type": req.ownership_type,
            "is_pep": bo.is_pep, "is_sanctioned": bo.is_sanctioned})
    db.commit(); db.refresh(bo)
    return {"beneficial_owner": {"id": bo.id, "session_id": bo.session_id,
        "full_name": bo.full_name, "ownership_type": bo.ownership_type,
        "ownership_pct": bo.ownership_pct, "is_pep": bo.is_pep,
        "is_sanctioned": bo.is_sanctioned, "unscr_checked": bo.unscr_checked,
        "edd_required": bo.edd_required, "verification_status": bo.verification_status,
        "created_at": bo.created_at.isoformat() if bo.created_at else None},
        "bfiu_ref": "BFIU Circular No. 29 s4.2"}

@router.get("/beneficial-owner/{session_id}", operation_id="bo_list")
def list_beneficial_owners(session_id: str, db: Session = Depends(get_tenant_db),
    actor: dict = Depends(get_current_user)):
    from app.db.models import BeneficialOwner
    bos = db.query(BeneficialOwner).filter_by(session_id=session_id).all()
    return {"session_id": session_id, "count": len(bos),
        "beneficial_owners": [{"id": b.id, "full_name": b.full_name,
            "ownership_type": b.ownership_type, "ownership_pct": b.ownership_pct,
            "is_pep": b.is_pep, "is_sanctioned": b.is_sanctioned,
            "edd_required": b.edd_required, "verification_status": b.verification_status,
            "unscr_checked": b.unscr_checked} for b in bos],
        "bfiu_ref": "BFIU Circular No. 29 s4.2"}

@router.delete("/beneficial-owner/record/{bo_id}", operation_id="bo_delete")
def delete_beneficial_owner(bo_id: str, db: Session = Depends(get_tenant_db),
    actor: dict = Depends(get_current_user)):
    from app.db.models import BeneficialOwner
    bo = db.query(BeneficialOwner).filter_by(id=bo_id).first()
    if not bo: raise HTTPException(404, f"BO {bo_id!r} not found")
    _audit(db, "BO_REMOVED", bo_id, bo.session_id, actor, {"full_name": bo.full_name})
    db.delete(bo); db.commit()
    return {"deleted": True, "bo_id": bo_id}

@router.post("/beneficial-owner/declaration", status_code=201, operation_id="bo_declaration")
def submit_bo_declaration(req: BODeclarationRequest, request: Request,
    db: Session = Depends(get_tenant_db), actor: dict = Depends(get_current_user)):
    from app.db.models import BeneficialOwner, BODeclaration
    profile = db.query(KYCProfile).filter_by(session_id=req.session_id).first()
    if not profile: raise HTTPException(404, f"KYC profile not found: {req.session_id!r}")
    bos = db.query(BeneficialOwner).filter_by(session_id=req.session_id).all()
    if req.has_beneficial_owner and not bos:
        raise HTTPException(400, "has_beneficial_owner=true but no BO records. Add via POST /kyc/beneficial-owner first.")
    if not req.has_beneficial_owner and bos:
        raise HTTPException(400, "has_beneficial_owner=false but BO records exist.")
    existing = db.query(BODeclaration).filter_by(session_id=req.session_id).first()
    ip = request.client.host if request.client else None
    actor_id = actor.get("user_id") or actor.get("sub")
    default_text = "I confirm no beneficial owner exists." if not req.has_beneficial_owner else "All beneficial owners have been disclosed."
    if existing:
        existing.has_beneficial_owner = req.has_beneficial_owner
        existing.declaration_text = req.declaration_text or default_text
        existing.declared_by = actor_id; existing.declaration_ip = ip
        decl = existing; created = False
    else:
        decl = BODeclaration(id=str(uuid.uuid4()), session_id=req.session_id,
            has_beneficial_owner=req.has_beneficial_owner,
            declaration_text=req.declaration_text or default_text,
            declared_by=actor_id, declaration_ip=ip)
        db.add(decl); created = True
    _audit(db, "BO_DECLARATION_SUBMITTED", decl.id, req.session_id, actor,
           {"has_beneficial_owner": req.has_beneficial_owner, "bo_count": len(bos)})
    db.commit()
    return {"declaration_id": decl.id, "session_id": req.session_id,
        "has_beneficial_owner": decl.has_beneficial_owner,
        "declaration_text": decl.declaration_text, "created": created,
        "bfiu_ref": "BFIU Circular No. 29 s4.2"}

@router.get("/beneficial-owner/compliance-status/{session_id}", operation_id="bo_compliance_status")
def bo_compliance_status(session_id: str, db: Session = Depends(get_tenant_db),
    actor: dict = Depends(get_current_user)):
    from app.db.models import BeneficialOwner, BODeclaration
    profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
    if not profile: raise HTTPException(404, f"KYC profile not found: {session_id!r}")
    bos = db.query(BeneficialOwner).filter_by(session_id=session_id).all()
    decl = db.query(BODeclaration).filter_by(session_id=session_id).first()
    pending = [b for b in bos if not b.unscr_checked]
    edd_inc = [b for b in bos if b.edd_required and b.verification_status != "VERIFIED"]
    ok = decl is not None and not pending and not edd_inc
    blockers = []
    if not decl: blockers.append("BO declaration not submitted")
    if pending:  blockers.append(f"{len(pending)} BO(s) awaiting UNSCR screening")
    if edd_inc:  blockers.append(f"{len(edd_inc)} BO(s) require EDD completion")
    return {"session_id": session_id, "kyc_type": profile.kyc_type,
        "declaration_submitted": decl is not None, "beneficial_owners": len(bos),
        "pending_screening": len(pending), "edd_required_count": len(edd_inc),
        "bo_check_complete": ok, "blockers": blockers,
        "bfiu_ref": "BFIU Circular No. 29 s4.2"}
