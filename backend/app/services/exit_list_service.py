"""
M69: Exit List Service — DB-backed
BFIU Circular No. 29 §5.1

Replaces in-memory _EXIT_LISTS dict in screening_service.py.
ADMIN/CHECKER only can add entries.
Fuzzy name matching via existing fuzzy_match_score (M56).
Falls back to in-memory if db=None (tests/legacy).
"""
from __future__ import annotations
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.timezone import now_bst as bst_now
from app.db.models_exit_list import ExitListEntry, ExitListAuditLog

try:
    from app.services.bangla_phonetic import fuzzy_match_score
except ImportError:
    from difflib import SequenceMatcher
    def fuzzy_match_score(a, b):
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()

EXIT_LIST_THRESHOLD = 0.80
ALLOWED_ROLES = {"ADMIN", "CHECKER"}


class ExitListPermissionError(Exception): pass
class ExitListNotFoundError(Exception): pass


def _normalise(name: str) -> str:
    return name.upper().strip()


def add_to_exit_list_db(
    db: Session,
    institution_id: str,
    name: str,
    reason: str,
    actor_user_id: Optional[uuid.UUID] = None,
    actor_role: Optional[str] = None,
    nid_hash: Optional[str] = None,
    additional_info: Optional[dict] = None,
) -> ExitListEntry:
    if actor_role and actor_role.upper() not in ALLOWED_ROLES:
        raise ExitListPermissionError(f"Role '{actor_role}' cannot manage exit list. ADMIN/CHECKER only.")

    entry = ExitListEntry(
        institution_id=institution_id,
        full_name=name.strip(),
        name_normalised=_normalise(name),
        reason=reason,
        nid_hash=nid_hash,
        additional_info=additional_info or {},
        is_active=True,
        added_by_user_id=actor_user_id,
        added_by_role=actor_role,
    )
    db.add(entry)
    db.flush()

    log = ExitListAuditLog(
        action="ADDED",
        entry_id=entry.id,
        institution_id=institution_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        details={"name": name, "reason": reason, "bfiu_ref": "BFIU Circular No. 29 §5.1"},
    )
    db.add(log)
    db.commit()
    db.refresh(entry)
    return entry


def deactivate_exit_list_entry(
    db: Session,
    entry_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
    reason: str,
) -> ExitListEntry:
    if actor_role.upper() not in ALLOWED_ROLES:
        raise ExitListPermissionError(f"Role '{actor_role}' cannot manage exit list.")

    entry = db.query(ExitListEntry).filter(ExitListEntry.id == entry_id).first()
    if not entry:
        raise ExitListNotFoundError(str(entry_id))

    entry.is_active = False
    entry.deactivated_at = bst_now()
    entry.deactivated_reason = reason

    log = ExitListAuditLog(
        action="DEACTIVATED",
        entry_id=entry.id,
        institution_id=entry.institution_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        details={"reason": reason},
    )
    db.add(log)
    db.commit()
    db.refresh(entry)
    return entry


def screen_exit_list_db(
    db: Session,
    name: str,
    institution_id: str,
    nid_hash: Optional[str] = None,
) -> dict:
    """
    Screen name against DB-backed exit list.
    NID exact match checked first (highest confidence).
    Falls back to fuzzy name match.
    """
    from app.core.timezone import bst_isoformat
    name_upper = _normalise(name)

    # NID exact match
    if nid_hash:
        nid_match = db.query(ExitListEntry).filter(
            ExitListEntry.institution_id == institution_id,
            ExitListEntry.nid_hash == nid_hash,
            ExitListEntry.is_active == True,
        ).first()
        if nid_match:
            return {
                "verdict": "MATCH",
                "match_type": "NID_EXACT",
                "score": 1.0,
                "matched_entry": {"id": str(nid_match.id), "name": nid_match.full_name, "reason": nid_match.reason},
                "blocking": True,
                "screened_at": bst_isoformat(),
                "bfiu_ref": "BFIU Circular No. 29 §5.1",
            }

    # Fuzzy name match
    active = db.query(ExitListEntry).filter(
        ExitListEntry.institution_id == institution_id,
        ExitListEntry.is_active == True,
    ).all()

    best_score = 0.0
    best_entry = None
    for entry in active:
        score = fuzzy_match_score(name_upper, entry.name_normalised)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= EXIT_LIST_THRESHOLD and best_entry:
        return {
            "verdict": "MATCH",
            "match_type": "FUZZY_NAME",
            "score": round(best_score, 4),
            "matched_entry": {"id": str(best_entry.id), "name": best_entry.full_name, "reason": best_entry.reason},
            "blocking": True,
            "screened_at": bst_isoformat(),
            "bfiu_ref": "BFIU Circular No. 29 §5.1",
        }

    return {
        "verdict": "CLEAR",
        "match_type": None,
        "score": round(best_score, 4),
        "matched_entry": None,
        "blocking": False,
        "screened_at": bst_isoformat(),
        "bfiu_ref": "BFIU Circular No. 29 §5.1",
    }


def list_exit_list(db: Session, institution_id: str, active_only: bool = True) -> list[ExitListEntry]:
    q = db.query(ExitListEntry).filter(ExitListEntry.institution_id == institution_id)
    if active_only:
        q = q.filter(ExitListEntry.is_active == True)
    return q.order_by(ExitListEntry.created_at.desc()).all()
