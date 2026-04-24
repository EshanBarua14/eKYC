"""
M62: PEP Service — DB-backed PEP/IP screening
BFIU Circular No. 29 §4.2

Replaces in-memory _PEP_LIST in screening_service.py.
ADMIN only can add/edit/deactivate PEP entries.
Fuzzy name matching via existing fuzzy_match_score (M56 Bangla phonetic).
"""
from __future__ import annotations
import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.timezone import now_bst as bst_now
from app.db.models_pep import (
    PEPEntry, PEPListMeta, PEPAuditLog,
    PEPCategory, PEPStatus, PEPAuditAction,
)

# Reuse existing fuzzy matcher from M56
try:
    from app.services.bangla_phonetic import fuzzy_match_score
except ImportError:
    def fuzzy_match_score(a: str, b: str) -> float:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()

PEP_MATCH_THRESHOLD = 0.80

# ── Permission guard ───────────────────────────────────────────────────────
ADMIN_ROLES = {"ADMIN"}

class PEPPermissionError(Exception): pass
class PEPNotFoundError(Exception): pass


def _require_admin(actor_role: str) -> None:
    if actor_role.upper() not in ADMIN_ROLES:
        raise PEPPermissionError(
            f"Role '{actor_role}' cannot manage PEP entries. ADMIN only."
        )


def _audit(db, action, entry_id, actor_user_id, actor_role,
           before=None, after=None, notes=None):
    log = PEPAuditLog(
        action=action,
        pep_entry_id=entry_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        before_state=before,
        after_state=after,
        notes=notes,
    )
    db.add(log)


def _entry_to_dict(e: PEPEntry) -> dict:
    return {
        "id": str(e.id),
        "full_name_en": e.full_name_en,
        "full_name_bn": e.full_name_bn,
        "aliases": e.aliases,
        "date_of_birth": e.date_of_birth,
        "national_id": e.national_id,
        "category": e.category,
        "position": e.position,
        "ministry_or_org": e.ministry_or_org,
        "country": e.country,
        "risk_level": e.risk_level,
        "edd_required": e.edd_required,
        "status": e.status,
        "source": e.source,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────

def add_pep_entry(
    db: Session,
    actor_user_id: uuid.UUID,
    actor_role: str,
    full_name_en: str,
    category: str,
    full_name_bn: Optional[str] = None,
    aliases: Optional[list] = None,
    date_of_birth: Optional[str] = None,
    national_id: Optional[str] = None,
    passport_number: Optional[str] = None,
    nationality: str = "BD",
    position: Optional[str] = None,
    ministry_or_org: Optional[str] = None,
    country: str = "BD",
    risk_level: str = "HIGH",
    source: str = "MANUAL",
    source_reference: Optional[str] = None,
    notes: Optional[str] = None,
) -> PEPEntry:
    _require_admin(actor_role)

    entry = PEPEntry(
        full_name_en=full_name_en.upper().strip(),
        full_name_bn=full_name_bn,
        aliases=aliases or [],
        date_of_birth=date_of_birth,
        national_id=national_id,
        passport_number=passport_number,
        nationality=nationality,
        category=category,
        position=position,
        ministry_or_org=ministry_or_org,
        country=country,
        risk_level=risk_level,
        edd_required=True,  # BFIU §4.2: always EDD for PEP/IP
        status=PEPStatus.ACTIVE,
        source=source,
        source_reference=source_reference,
        notes=notes,
        added_by_user_id=actor_user_id,
        last_updated_by=actor_user_id,
    )
    db.add(entry)
    db.flush()

    _audit(db, PEPAuditAction.CREATED, entry.id,
           actor_user_id, actor_role,
           after=_entry_to_dict(entry),
           notes=f"PEP entry created: {full_name_en}")
    db.commit()
    db.refresh(entry)
    return entry


def update_pep_entry(
    db: Session,
    entry_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    **fields,
) -> PEPEntry:
    _require_admin(actor_role)

    entry = db.query(PEPEntry).filter(PEPEntry.id == entry_id).first()
    if not entry:
        raise PEPNotFoundError(str(entry_id))

    before = _entry_to_dict(entry)
    for k, v in fields.items():
        if hasattr(entry, k) and v is not None:
            setattr(entry, k, v)
    entry.last_updated_by = actor_user_id

    _audit(db, PEPAuditAction.UPDATED, entry.id,
           actor_user_id, actor_role,
           before=before, after=_entry_to_dict(entry))
    db.commit()
    db.refresh(entry)
    return entry


def deactivate_pep_entry(
    db: Session,
    entry_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    reason: str,
) -> PEPEntry:
    _require_admin(actor_role)

    entry = db.query(PEPEntry).filter(PEPEntry.id == entry_id).first()
    if not entry:
        raise PEPNotFoundError(str(entry_id))

    before = _entry_to_dict(entry)
    entry.status = PEPStatus.INACTIVE
    entry.deactivated_at = bst_now()
    entry.last_updated_by = actor_user_id

    _audit(db, PEPAuditAction.DEACTIVATED, entry.id,
           actor_user_id, actor_role,
           before=before, after=_entry_to_dict(entry), notes=reason)
    db.commit()
    db.refresh(entry)
    return entry


def list_pep_entries(
    db: Session,
    category: Optional[str] = None,
    status: Optional[str] = PEPStatus.ACTIVE,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PEPEntry]:
    q = db.query(PEPEntry)
    if category:
        q = q.filter(PEPEntry.category == category)
    if status:
        q = q.filter(PEPEntry.status == status)
    if search:
        term = f"%{search.upper()}%"
        q = q.filter(
            or_(
                func.upper(PEPEntry.full_name_en).like(term),
                func.upper(PEPEntry.full_name_bn).like(term),
            )
        )
    return q.order_by(PEPEntry.full_name_en).offset(offset).limit(limit).all()


# ── Screening ─────────────────────────────────────────────────────────────

def screen_pep_db(
    db: Session,
    name: str,
    national_id: Optional[str] = None,
) -> dict:
    """
    Screen name against DB-backed PEP list.
    BFIU §4.2: mandatory for Regular eKYC.
    Returns MATCH/NO_MATCH with best score and matched entry.
    """
    name_upper = name.upper().strip()

    # 1. Exact NID match (highest confidence)
    if national_id:
        nid_match = db.query(PEPEntry).filter(
            PEPEntry.national_id == national_id,
            PEPEntry.status == PEPStatus.ACTIVE,
        ).first()
        if nid_match:
            _audit(db, PEPAuditAction.MATCHED, nid_match.id,
                   None, "SYSTEM",
                   notes=f"NID exact match: {national_id}")
            db.commit()
            return {
                "verdict": "MATCH",
                "match_type": "NID_EXACT",
                "score": 1.0,
                "matched_entry": _entry_to_dict(nid_match),
                "edd_required": True,
                "bfiu_ref": "BFIU Circular No. 29 §4.2",
            }

    # 2. Fuzzy name match against active entries
    active = db.query(PEPEntry).filter(
        PEPEntry.status == PEPStatus.ACTIVE
    ).all()

    best_score = 0.0
    best_entry = None

    for entry in active:
        # Check primary name
        score = fuzzy_match_score(name_upper, entry.full_name_en)
        if entry.full_name_bn:
            score = max(score, fuzzy_match_score(name_upper, entry.full_name_bn))
        # Check aliases
        for alias in (entry.aliases or []):
            score = max(score, fuzzy_match_score(name_upper, str(alias).upper()))

        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= PEP_MATCH_THRESHOLD and best_entry:
        _audit(db, PEPAuditAction.MATCHED, best_entry.id,
               None, "SYSTEM",
               notes=f"Fuzzy match: {name} score={best_score:.3f}")
        db.commit()
        return {
            "verdict": "MATCH",
            "match_type": "FUZZY_NAME",
            "score": round(best_score, 4),
            "matched_entry": _entry_to_dict(best_entry),
            "edd_required": True,
            "bfiu_ref": "BFIU Circular No. 29 §4.2",
        }

    return {
        "verdict": "NO_MATCH",
        "match_type": None,
        "score": round(best_score, 4),
        "matched_entry": None,
        "edd_required": False,
        "bfiu_ref": "BFIU Circular No. 29 §4.2",
    }


def get_pep_list_meta(db: Session) -> dict:
    meta = db.query(PEPListMeta).filter(
        PEPListMeta.list_name == "BFIU_PEP_IP"
    ).first()
    total = db.query(PEPEntry).filter(
        PEPEntry.status == PEPStatus.ACTIVE
    ).count()
    return {
        "list_name": "BFIU_PEP_IP",
        "total_active_entries": total,
        "version": meta.version if meta else "1.0",
        "last_updated_at": meta.last_updated_at.isoformat() if meta else None,
        "bfiu_ref": "BFIU Circular No. 29 §4.2",
    }
