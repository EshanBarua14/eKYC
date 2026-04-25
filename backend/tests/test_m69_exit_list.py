"""
M69 Tests: Exit list DB-backed + screening
BFIU Circular No. 29 §5.1
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.db.models_exit_list import ExitListEntry, ExitListAuditLog
from app.services.exit_list_service import (
    ExitListPermissionError, ExitListNotFoundError,
    add_to_exit_list_db, deactivate_exit_list_entry,
    screen_exit_list_db, list_exit_list,
    EXIT_LIST_THRESHOLD, ALLOWED_ROLES,
)

BST = timezone(timedelta(hours=6))


def _make_entry(name="BLOCKED PERSON", active=True, institution="inst-001"):
    e = ExitListEntry()
    e.id = uuid.uuid4()
    e.institution_id = institution
    e.full_name = name
    e.name_normalised = name.upper()
    e.reason = "Fraud"
    e.nid_hash = None
    e.additional_info = {}
    e.is_active = active
    e.added_by_user_id = uuid.uuid4()
    e.added_by_role = "ADMIN"
    e.deactivated_at = None
    e.deactivated_reason = None
    e.created_at = datetime.now(BST)
    e.updated_at = datetime.now(BST)
    return e


def _mock_db(entries=None, first=None):
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    q.all.return_value = entries or []
    q.order_by.return_value = q
    q.count.return_value = len(entries) if entries else 0
    db.query.return_value = q
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda x: None)
    return db


# ── T01-T04: Permissions ──────────────────────────────────────────────────
def test_T01_admin_can_add():
    db = _mock_db()
    entry = add_to_exit_list_db(db, "inst-001", "BLOCKED PERSON", "Fraud",
                                actor_role="ADMIN")
    assert db.add.called

def test_T02_checker_can_add():
    db = _mock_db()
    add_to_exit_list_db(db, "inst-001", "BLOCKED PERSON", "Fraud",
                        actor_role="CHECKER")
    assert db.add.called

def test_T03_agent_cannot_add():
    db = _mock_db()
    with pytest.raises(ExitListPermissionError):
        add_to_exit_list_db(db, "inst-001", "BLOCKED PERSON", "Fraud",
                            actor_role="AGENT")

def test_T04_auditor_cannot_add():
    db = _mock_db()
    with pytest.raises(ExitListPermissionError):
        add_to_exit_list_db(db, "inst-001", "BLOCKED PERSON", "Fraud",
                            actor_role="AUDITOR")


# ── T05-T08: Add + deactivate ─────────────────────────────────────────────
def test_T05_add_creates_entry_and_audit():
    db = _mock_db()
    add_to_exit_list_db(db, "inst-001", "TEST PERSON", "Fraud",
                        actor_role="ADMIN")
    # db.add called twice: entry + audit log
    assert db.add.call_count >= 2

def test_T06_deactivate_sets_inactive():
    entry = _make_entry()
    db = _mock_db(first=entry)
    result = deactivate_exit_list_entry(db, entry.id, uuid.uuid4(), "ADMIN", "Resolved")
    assert result.is_active == False
    assert result.deactivated_at is not None

def test_T07_deactivate_nonexistent_raises():
    db = _mock_db(first=None)
    with pytest.raises(ExitListNotFoundError):
        deactivate_exit_list_entry(db, uuid.uuid4(), uuid.uuid4(), "ADMIN", "reason")

def test_T08_deactivate_checker_blocked():
    entry = _make_entry()
    db = _mock_db(first=entry)
    with pytest.raises(ExitListPermissionError):
        deactivate_exit_list_entry(db, entry.id, uuid.uuid4(), "MAKER", "reason")


# ── T09-T14: Screening ────────────────────────────────────────────────────
def test_T09_exact_nid_match():
    entry = _make_entry()
    entry.nid_hash = "abc123hash"
    db = _mock_db(first=entry, entries=[entry])
    result = screen_exit_list_db(db, "ANY NAME", "inst-001", nid_hash="abc123hash")
    assert result["verdict"] == "MATCH"
    assert result["match_type"] == "NID_EXACT"
    assert result["blocking"] == True

def test_T10_fuzzy_match():
    entry = _make_entry("BLOCKED PERSON")
    db = _mock_db(entries=[entry])
    with patch("app.services.exit_list_service.fuzzy_match_score", return_value=0.95):
        result = screen_exit_list_db(db, "BLOCKED PERSON", "inst-001")
    assert result["verdict"] == "MATCH"
    assert result["blocking"] == True

def test_T11_no_match_clear():
    db = _mock_db(entries=[])
    result = screen_exit_list_db(db, "UNKNOWN PERSON", "inst-001")
    assert result["verdict"] == "CLEAR"
    assert result["blocking"] == False

def test_T12_below_threshold_clear():
    entry = _make_entry("BLOCKED PERSON")
    db = _mock_db(entries=[entry])
    with patch("app.services.exit_list_service.fuzzy_match_score", return_value=0.50):
        result = screen_exit_list_db(db, "DIFFERENT NAME", "inst-001")
    assert result["verdict"] == "CLEAR"

def test_T13_bfiu_ref_in_result():
    db = _mock_db(entries=[])
    result = screen_exit_list_db(db, "TEST", "inst-001")
    assert "bfiu_ref" in result
    assert "5.1" in result["bfiu_ref"]

def test_T14_threshold_is_80():
    assert EXIT_LIST_THRESHOLD == 0.80


# ── T15-T18: Fallback ─────────────────────────────────────────────────────
def test_T15_screening_service_fallback_no_db():
    from app.services.screening_service import screen_exit_list
    result = screen_exit_list("UNKNOWN PERSON", "inst-001", db=None)
    assert result["verdict"] == "CLEAR"
    assert result.get("source") == "MEMORY"

def test_T16_migration_file_exists():
    import os
    assert os.path.exists("alembic/versions/m69_exit_list_tables.py")

def test_T17_allowed_roles():
    assert "ADMIN" in ALLOWED_ROLES
    assert "CHECKER" in ALLOWED_ROLES
    assert "AGENT" not in ALLOWED_ROLES

def test_T18_models_exist():
    from app.db.models_exit_list import ExitListEntry, ExitListAuditLog
    assert ExitListEntry.__tablename__ == "exit_list_entries"
    assert ExitListAuditLog.__tablename__ == "exit_list_audit_log"
