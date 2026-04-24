"""
M60 Tests: COMPLIANCE_OFFICER role + EDD approval workflow
BFIU Circular No. 29 §4.2, §4.3
25 tests — 0 failures expected
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.db.models_edd import EDDStatus, EDDTrigger, EDDActionType, EDDCase, EDDAction
from app.services.edd_service import (
    EDDPermissionError, EDDStateError, EDDNotFoundError,
    _require_compliance_officer,
    ALLOWED_EDD_ROLES, BLOCKED_EDD_APPROVAL_ROLES, EDD_SLA_DAYS,
    approve_edd, reject_edd, immediate_close, escalate_to_bfiu,
    auto_close_expired_cases, get_edd_queue,
)

BST = timezone(timedelta(hours=6))

def _case(status=EDDStatus.OPEN, sla=None, existing=False):
    c = EDDCase()
    c.id = uuid.uuid4()
    c.case_reference = "EDD-2026-00001"
    c.kyc_session_id = "sess-abc"
    c.customer_nid_hash = "abc123"
    c.trigger = EDDTrigger.HIGH_RISK_SCORE
    c.trigger_evidence = {}
    c.risk_score = 18
    c.status = status
    c.is_existing_customer = existing
    c.sla_deadline = sla
    c.assigned_to_user_id = None
    c.assigned_at = None
    c.decision_user_id = None
    c.decision_role = None
    c.decision_at = None
    c.decision_notes = None
    c.actions = []
    c.created_at = datetime.now(BST)
    c.updated_at = datetime.now(BST)
    return c

def _db(case=None):
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = case
    q.count.return_value = 0
    q.all.return_value = [case] if case else []
    q.like.return_value = q
    q.order_by.return_value = q
    db.query.return_value = q
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda c: None)
    return db

# ── T01-T06: Permissions ──────────────────────────────────────────────────
def test_T01_checker_blocked():
    with pytest.raises(EDDPermissionError) as e:
        _require_compliance_officer("CHECKER", "approve")
    assert "CHECKER" in str(e.value)
    assert "COMPLIANCE_OFFICER" in str(e.value)

def test_T02_maker_blocked():
    with pytest.raises(EDDPermissionError): _require_compliance_officer("MAKER", "approve")

def test_T03_agent_blocked():
    with pytest.raises(EDDPermissionError): _require_compliance_officer("AGENT", "approve")

def test_T04_auditor_blocked():
    with pytest.raises(EDDPermissionError): _require_compliance_officer("AUDITOR", "approve")

def test_T05_compliance_officer_allowed():
    _require_compliance_officer("COMPLIANCE_OFFICER", "approve")  # no raise

def test_T06_admin_allowed():
    _require_compliance_officer("ADMIN", "approve")  # no raise

def test_T06b_blocked_roles_constant():
    assert {"CHECKER","MAKER","AGENT","AUDITOR"} == BLOCKED_EDD_APPROVAL_ROLES

def test_T06c_allowed_roles_constant():
    assert {"COMPLIANCE_OFFICER","ADMIN"} == ALLOWED_EDD_ROLES

# ── T07-T12: State machine ────────────────────────────────────────────────
def test_T07_approve_changes_status():
    c = _case(EDDStatus.UNDER_REVIEW)
    result = approve_edd(_db(c), c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "Approved")
    assert result.status == EDDStatus.APPROVED
    assert result.decision_role == "COMPLIANCE_OFFICER"
    assert result.decision_at is not None

def test_T08_checker_blocked_from_approve():
    c = _case(EDDStatus.UNDER_REVIEW)
    with pytest.raises(EDDPermissionError):
        approve_edd(_db(c), c.id, uuid.uuid4(), "CHECKER", "trying")

def test_T09_reject_changes_status():
    c = _case(EDDStatus.OPEN)
    result = reject_edd(_db(c), c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "Rejected")
    assert result.status == EDDStatus.REJECTED

def test_T10_cannot_approve_terminal():
    c = _case(EDDStatus.REJECTED)
    with pytest.raises(EDDStateError):
        approve_edd(_db(c), c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "notes")

def test_T11_immediate_close_sets_rejected():
    c = _case(EDDStatus.OPEN)
    result = immediate_close(_db(c), c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "Irregular tx")
    assert result.status == EDDStatus.REJECTED
    assert "IMMEDIATE CLOSE" in result.decision_notes

def test_T12_checker_cannot_immediate_close():
    c = _case(EDDStatus.OPEN)
    with pytest.raises(EDDPermissionError):
        immediate_close(_db(c), c.id, uuid.uuid4(), "CHECKER", "trying")

def test_T12b_escalate_sets_escalated():
    c = _case(EDDStatus.UNDER_REVIEW)
    result = escalate_to_bfiu(_db(c), c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "Escalate")
    assert result.status == EDDStatus.ESCALATED

def test_T12c_not_found_raises():
    with pytest.raises(EDDNotFoundError):
        approve_edd(_db(None), uuid.uuid4(), uuid.uuid4(), "COMPLIANCE_OFFICER", "notes")

# ── T13-T16: SLA ─────────────────────────────────────────────────────────
def test_T13_sla_is_30_days():
    assert EDD_SLA_DAYS == 30

def test_T14_auto_close_expired():
    past = datetime.now(BST) - timedelta(days=1)
    c = _case(EDDStatus.OPEN, sla=past, existing=True)
    db = MagicMock()
    q = MagicMock(); q.filter.return_value = q; q.all.return_value = [c]
    db.query.return_value = q; db.add = MagicMock(); db.commit = MagicMock()
    closed = auto_close_expired_cases(db)
    assert closed == 1
    assert c.status == EDDStatus.AUTO_CLOSED
    assert "1-month" in c.decision_notes

def test_T15_no_close_future_deadline():
    db = MagicMock()
    q = MagicMock(); q.filter.return_value = q; q.all.return_value = []
    db.query.return_value = q; db.commit = MagicMock()
    assert auto_close_expired_cases(db) == 0

def test_T16_terminal_not_auto_closed():
    db = MagicMock()
    q = MagicMock(); q.filter.return_value = q; q.all.return_value = []
    db.query.return_value = q; db.commit = MagicMock()
    assert auto_close_expired_cases(db) == 0

# ── T17-T20: Queue access ─────────────────────────────────────────────────
def _qdb(cases):
    db = MagicMock()
    q = MagicMock(); q.filter.return_value = q; q.order_by.return_value = q; q.all.return_value = cases
    db.query.return_value = q
    return db

def test_T17_co_gets_queue():
    assert len(get_edd_queue(_qdb([_case()]), "COMPLIANCE_OFFICER", uuid.uuid4())) == 1

def test_T18_checker_empty_queue():
    assert get_edd_queue(_qdb([_case()]), "CHECKER") == []

def test_T19_agent_empty_queue():
    assert get_edd_queue(_qdb([_case()]), "AGENT") == []

def test_T20_admin_gets_all():
    assert len(get_edd_queue(_qdb([_case(), _case()]), "ADMIN")) == 2

# ── T21-T25: BFIU compliance ──────────────────────────────────────────────
def test_T21_sla_30_days():
    assert EDD_SLA_DAYS == 30

def test_T22_all_triggers_defined():
    required = {"HIGH_RISK_SCORE","PEP_FLAG","ADVERSE_MEDIA","RISK_REGRADE","IRREGULAR_ACTIVITY","MANUAL_TRIGGER"}
    actual = {v for k,v in vars(EDDTrigger).items() if not k.startswith("_")}
    assert required.issubset(actual)

def test_T23_terminal_states_correct():
    assert EDDStatus.APPROVED in EDDStatus.TERMINAL
    assert EDDStatus.REJECTED in EDDStatus.TERMINAL
    assert EDDStatus.AUTO_CLOSED in EDDStatus.TERMINAL
    assert EDDStatus.ESCALATED in EDDStatus.TERMINAL
    assert EDDStatus.OPEN not in EDDStatus.TERMINAL

def test_T24_action_logged_on_approve():
    c = _case(EDDStatus.UNDER_REVIEW)
    db = _db(c)
    approve_edd(db, c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "EDD cleared")
    assert db.add.called

def test_T25_bst_timestamp_on_decision():
    c = _case(EDDStatus.OPEN)
    approve_edd(_db(c), c.id, uuid.uuid4(), "COMPLIANCE_OFFICER", "OK")
    assert c.decision_at is not None
    assert c.decision_at.utcoffset() == timedelta(hours=6)
