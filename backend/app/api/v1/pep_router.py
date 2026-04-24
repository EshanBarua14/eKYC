"""
M62: PEP Admin Management API
BFIU Circular No. 29 §4.2

ADMIN only: add, update, deactivate PEP entries.
All roles: read PEP list meta.
SYSTEM: screen_pep_db called from screening_service.
"""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.v1.routes.auth import get_current_user
from app.middleware.rbac import require_admin
from app.services.pep_service import (
    add_pep_entry, update_pep_entry, deactivate_pep_entry,
    list_pep_entries, get_pep_list_meta, screen_pep_db,
    PEPPermissionError, PEPNotFoundError,
)
from app.db.models_pep import PEPStatus

router = APIRouter(prefix="/v1/pep", tags=["PEP/IP Management §4.2"])


class AddPEPRequest(BaseModel):
    full_name_en: str = Field(..., min_length=2, max_length=255)
    full_name_bn: Optional[str] = None
    aliases: Optional[list[str]] = []
    date_of_birth: Optional[str] = None
    national_id: Optional[str] = None
    passport_number: Optional[str] = None
    nationality: str = "BD"
    category: str = Field(..., description="PEP|IP|PEP_FAMILY|PEP_ASSOCIATE")
    position: Optional[str] = None
    ministry_or_org: Optional[str] = None
    country: str = "BD"
    risk_level: str = "HIGH"
    source: str = "MANUAL"
    source_reference: Optional[str] = None
    notes: Optional[str] = None


class UpdatePEPRequest(BaseModel):
    full_name_en: Optional[str] = None
    full_name_bn: Optional[str] = None
    position: Optional[str] = None
    ministry_or_org: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    risk_level: Optional[str] = None


class DeactivateRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class ScreenRequest(BaseModel):
    name: str = Field(..., min_length=2)
    national_id: Optional[str] = None


def _handle(e):
    if isinstance(e, PEPPermissionError):
        raise HTTPException(403, str(e))
    if isinstance(e, PEPNotFoundError):
        raise HTTPException(404, f"PEP entry not found: {e}")
    raise e


@router.get("/meta")
def pep_meta(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """PEP list stats — all authenticated roles."""
    return get_pep_list_meta(db)


@router.get("/entries")
def list_entries(
    category: Optional[str] = None,
    status: Optional[str] = PEPStatus.ACTIVE,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List PEP entries. ADMIN/AUDITOR/COMPLIANCE_OFFICER."""
    role = (current_user.get("role") or "").upper()
    if role not in {"ADMIN", "AUDITOR", "COMPLIANCE_OFFICER"}:
        raise HTTPException(403, "Access denied")
    entries = list_pep_entries(db, category, status, search, limit, offset)
    return [_entry_dict(e) for e in entries]


def _entry_dict(e):
    return {
        "id": str(e.id),
        "full_name_en": e.full_name_en,
        "full_name_bn": e.full_name_bn,
        "aliases": e.aliases,
        "category": e.category,
        "position": e.position,
        "ministry_or_org": e.ministry_or_org,
        "country": e.country,
        "risk_level": e.risk_level,
        "edd_required": e.edd_required,
        "status": e.status,
        "national_id": e.national_id,
        "source": e.source,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }


@router.post("/entries", status_code=201)
def add_entry(
    body: AddPEPRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Add PEP entry. ADMIN only."""
    try:
        entry = add_pep_entry(
            db,
            actor_user_id=uuid.UUID(current_user["user_id"]),
            actor_role=current_user["role"],
            **body.model_dump(),
        )
    except Exception as e:
        _handle(e)
    return {"id": str(entry.id), "case_reference": entry.full_name_en, "status": entry.status}


@router.patch("/entries/{entry_id}")
def update_entry(
    entry_id: uuid.UUID,
    body: UpdatePEPRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Update PEP entry. ADMIN only."""
    try:
        entry = update_pep_entry(
            db, entry_id,
            actor_user_id=uuid.UUID(current_user["user_id"]),
            actor_role=current_user["role"],
            **{k: v for k, v in body.model_dump().items() if v is not None},
        )
    except Exception as e:
        _handle(e)
    return _entry_dict(entry)


@router.post("/entries/{entry_id}/deactivate")
def deactivate_entry(
    entry_id: uuid.UUID,
    body: DeactivateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Deactivate PEP entry. ADMIN only. Record retained for audit."""
    try:
        entry = deactivate_pep_entry(
            db, entry_id,
            actor_user_id=uuid.UUID(current_user["user_id"]),
            actor_role=current_user["role"],
            reason=body.reason,
        )
    except Exception as e:
        _handle(e)
    return {"id": str(entry.id), "status": entry.status,
            "deactivated_at": entry.deactivated_at.isoformat()}


@router.post("/screen")
def screen(
    body: ScreenRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Screen name against PEP/IP DB.
    Called internally by screening_service for Regular eKYC.
    Also available for manual checks by ADMIN/COMPLIANCE_OFFICER.
    """
    role = (current_user.get("role") or "").upper()
    if role not in {"ADMIN", "COMPLIANCE_OFFICER", "CHECKER", "MAKER"}:
        raise HTTPException(403, "Access denied")
    return screen_pep_db(db, body.name, body.national_id)
