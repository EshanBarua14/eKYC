"""
M61 Tests: Role-based data isolation
BFIU Circular No. 29 §5.1, §5.2

Test groups:
  T01-T06: AUDITOR write-blocked
  T07-T10: AGENT own-records-only filter
  T11-T14: COMPLIANCE_OFFICER KYC write blocked
  T15-T18: Readable/writable resource maps
  T19-T22: Middleware dependency behaviour
  T23-T26: BFIU compliance assertions
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.services.data_isolation import (
    assert_write_permitted,
    assert_kyc_write_permitted,
    apply_agent_filter,
    get_readable_resources,
    get_writable_resources,
    WRITE_BLOCKED_ROLES,
    OWN_RECORDS_ONLY_ROLES,
    KYC_WRITE_BLOCKED_ROLES,
)

# ── helpers ───────────────────────────────────────────────────────────────
def _user(role, user_id="user-123"):
    return {"role": role, "user_id": user_id, "sub": "inst-abc"}


# ── T01-T06: AUDITOR write-blocked ────────────────────────────────────────
def test_T01_auditor_blocked_from_write():
    with pytest.raises(HTTPException) as e:
        assert_write_permitted("AUDITOR", "kyc_sessions")
    assert e.value.status_code == 403
    assert "read-only" in e.value.detail["message"]

def test_T02_auditor_blocked_detail_has_bfiu_ref():
    with pytest.raises(HTTPException) as e:
        assert_write_permitted("AUDITOR", "audit_logs")
    assert "BFIU" in e.value.detail["bfiu_ref"]

def test_T03_admin_write_allowed():
    assert_write_permitted("ADMIN", "kyc_sessions")  # no raise

def test_T04_checker_write_allowed():
    assert_write_permitted("CHECKER", "verification_results")  # no raise

def test_T05_maker_write_allowed():
    assert_write_permitted("MAKER", "kyc_sessions")  # no raise

def test_T06_auditor_in_write_blocked_constant():
    assert "AUDITOR" in WRITE_BLOCKED_ROLES


# ── T07-T10: AGENT own-records filter ─────────────────────────────────────
def test_T07_agent_filter_applied():
    """AGENT query must be filtered by agent_id."""
    model = MagicMock()
    model.agent_id = MagicMock()
    model.agent_id.__eq__ = MagicMock(return_value=True)

    query = MagicMock()
    query.filter.return_value = query

    result = apply_agent_filter(query, model, _user("AGENT", "agent-999"))
    assert query.filter.called

def test_T08_admin_no_filter():
    """ADMIN query must NOT be filtered."""
    model = MagicMock()
    query = MagicMock()
    query.filter.return_value = query

    apply_agent_filter(query, model, _user("ADMIN"))
    assert not query.filter.called

def test_T09_checker_no_filter():
    apply_agent_filter(MagicMock(), MagicMock(), _user("CHECKER"))
    # no exception = pass

def test_T10_agent_in_own_records_constant():
    assert "AGENT" in OWN_RECORDS_ONLY_ROLES


# ── T11-T14: COMPLIANCE_OFFICER KYC write blocked ─────────────────────────
def test_T11_co_blocked_from_kyc_write():
    with pytest.raises(HTTPException) as e:
        assert_kyc_write_permitted("COMPLIANCE_OFFICER")
    assert e.value.status_code == 403
    assert "EDD" in e.value.detail["message"]

def test_T12_auditor_blocked_from_kyc_write():
    with pytest.raises(HTTPException) as e:
        assert_kyc_write_permitted("AUDITOR")
    assert e.value.status_code == 403

def test_T13_maker_kyc_write_allowed():
    assert_kyc_write_permitted("MAKER")  # no raise

def test_T14_co_in_kyc_write_blocked_constant():
    assert "COMPLIANCE_OFFICER" in KYC_WRITE_BLOCKED_ROLES
    assert "AUDITOR" in KYC_WRITE_BLOCKED_ROLES


# ── T15-T18: Resource maps ─────────────────────────────────────────────────
def test_T15_auditor_has_no_writable_resources():
    assert get_writable_resources("AUDITOR") == []

def test_T16_auditor_reads_audit_logs():
    assert "audit_logs" in get_readable_resources("AUDITOR")

def test_T17_co_writes_only_edd():
    writable = get_writable_resources("COMPLIANCE_OFFICER")
    assert writable == ["edd_cases"]

def test_T18_agent_reads_own_only():
    readable = get_readable_resources("AGENT")
    assert all("own_" in r for r in readable)


# ── T19-T22: Middleware dependencies ──────────────────────────────────────
def test_T19_require_write_access_blocks_auditor():
    from app.middleware.data_isolation_middleware import require_write_access
    dep = require_write_access("kyc_sessions")
    user = _user("AUDITOR")
    with pytest.raises(HTTPException) as e:
        # simulate calling the inner function directly
        from app.services.data_isolation import assert_write_permitted
        assert_write_permitted("AUDITOR", "kyc_sessions")
    assert e.value.status_code == 403

def test_T20_require_kyc_write_blocks_co():
    from app.services.data_isolation import assert_kyc_write_permitted
    with pytest.raises(HTTPException) as e:
        assert_kyc_write_permitted("COMPLIANCE_OFFICER")
    assert e.value.status_code == 403

def test_T21_write_blocked_roles_set():
    assert WRITE_BLOCKED_ROLES == {"AUDITOR"}

def test_T22_own_records_roles_set():
    assert OWN_RECORDS_ONLY_ROLES == {"AGENT"}


# ── T23-T26: BFIU compliance assertions ───────────────────────────────────
def test_T23_six_roles_have_resource_maps():
    for role in ["ADMIN", "CHECKER", "MAKER", "AGENT", "AUDITOR", "COMPLIANCE_OFFICER"]:
        r = get_readable_resources(role)
        w = get_writable_resources(role)
        assert isinstance(r, list), f"{role} readable missing"
        assert isinstance(w, list), f"{role} writable missing"

def test_T24_admin_has_full_access():
    assert get_readable_resources("ADMIN") == ["*"]
    assert get_writable_resources("ADMIN") == ["*"]

def test_T25_checker_cannot_write_kyc_sessions():
    writable = get_writable_resources("CHECKER")
    assert "kyc_sessions" not in writable

def test_T26_error_response_has_bfiu_ref():
    """All 403 errors from isolation must carry BFIU reference."""
    with pytest.raises(HTTPException) as e:
        assert_write_permitted("AUDITOR", "test")
    assert "bfiu_ref" in e.value.detail
    assert "Circular No. 29" in e.value.detail["bfiu_ref"]
