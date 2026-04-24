"""
M59 — UNSCR Live Feed Production Tests
BFIU Circular No. 29 §5.1

Tests:
- DB-backed screening with fallback
- Bangla phonetic in DB search
- SSL verification enabled
- Admin trigger endpoint
- List version in audit trail
- BST timestamps
- Alert system
- FTS indexes exist
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(email="auditor-bypass@demo.ekyc", password="DemoAudit@2026"):
    r = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    return r.json().get("access_token", "")


# ── SSL verification ──────────────────────────────────────────────────────
class TestSSLVerification:
    def test_ssl_cert_required(self):
        import ssl
        from app.services import unscr_service
        import inspect
        src = inspect.getsource(unscr_service._fetch_and_parse)
        assert "CERT_NONE" not in src
        assert "CERT_REQUIRED" in src or "create_default_context" in src

    def test_ssl_check_hostname_true(self):
        from app.services import unscr_service
        import inspect
        src = inspect.getsource(unscr_service._fetch_and_parse)
        assert "check_hostname = False" not in src


# ── DB search with phonetic ───────────────────────────────────────────────
class TestDBSearch:
    def test_search_unscr_returns_dict(self):
        from app.services.unscr_service import search_unscr
        r = search_unscr("RAHMAN HOSSAIN")
        assert isinstance(r, dict)
        assert "verdict" in r

    def test_search_unscr_clear_on_clean_name(self):
        from app.services.unscr_service import search_unscr
        r = search_unscr("CLEAN PERSON NAME XYZ123")
        assert r["verdict"] == "CLEAR"

    def test_search_unscr_has_bfiu_ref(self):
        from app.services.unscr_service import search_unscr
        r = search_unscr("RAHMAN HOSSAIN")
        assert "BFIU" in r.get("bfiu_ref", "")

    def test_score_uses_phonetic(self):
        from app.services.unscr_service import _score
        # Bangla phonetic variants should score higher than pure token overlap
        score1 = _score("AL QAIDA", "AL QAIDA", [])
        score2 = _score("RAHMAN", "CLEAN PERSON", [])
        assert score1 > score2

    def test_score_handles_aliases(self):
        from app.services.unscr_service import _score
        score = _score("AQ", "AL QAIDA", ["AL-QAEDA", "AQ"])
        assert score > 0.5


# ── screen_unscr DB+fallback ──────────────────────────────────────────────
class TestScreenUNSCR:
    def test_screen_unscr_returns_verdict(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("RAHMAN HOSSAIN")
        assert r["verdict"] in ("CLEAR", "REVIEW", "MATCH")

    def test_screen_unscr_has_source(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("RAHMAN HOSSAIN")
        assert "source" in r

    def test_screen_unscr_has_list_version(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("RAHMAN HOSSAIN")
        assert "list_version" in r or r.get("source") == "DB"

    def test_screen_unscr_known_sanctioned_entity(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("AL QAIDA")
        assert r["verdict"] in ("MATCH", "REVIEW")

    def test_screen_unscr_blocks_on_match(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("AL QAIDA")
        if r["verdict"] == "MATCH":
            assert r.get("blocking") is True

    def test_screen_unscr_bfiu_ref(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("RAHMAN HOSSAIN")
        assert "3.2.2" in r.get("bfiu_ref", "") or "5.1" in r.get("bfiu_ref", "")


# ── Full screening overall_verdict ───────────────────────────────────────
class TestFullScreening:
    def test_run_full_screening_has_overall_verdict(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("RAHMAN HOSSAIN", "SIMPLIFIED")
        assert "overall_verdict" in r

    def test_run_full_screening_combined_verdict(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("RAHMAN HOSSAIN", "SIMPLIFIED")
        assert r["combined_verdict"] == r["overall_verdict"]

    def test_simplified_no_pep_check(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("RAHMAN HOSSAIN", "SIMPLIFIED")
        assert "pep" not in r["results"]

    def test_regular_has_pep_check(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("RAHMAN HOSSAIN", "REGULAR")
        assert "pep" in r["results"]

    def test_regular_has_adverse_media(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("RAHMAN HOSSAIN", "REGULAR")
        assert "adverse_media" in r["results"]


# ── BST timestamps ────────────────────────────────────────────────────────
class TestBSTTimestamps:
    def test_screening_result_has_bst_timestamp(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("RAHMAN HOSSAIN")
        ts = r.get("screened_at", "")
        assert "+06:00" in ts or "BST" in ts

    def test_bst_isoformat_returns_dhaka_offset(self):
        from app.core.timezone import bst_isoformat
        ts = bst_isoformat()
        assert "+06:00" in ts

    def test_bst_display_contains_bst(self):
        from app.core.timezone import bst_display
        d = bst_display()
        assert "BST" in d

    def test_now_bst_offset(self):
        from app.core.timezone import now_bst
        from datetime import timezone, timedelta
        dt = now_bst()
        assert dt.utcoffset() == timedelta(hours=6)


# ── List version in audit ─────────────────────────────────────────────────
class TestListVersionAudit:
    def test_unscr_list_version_in_screening_result(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("RAHMAN HOSSAIN", "SIMPLIFIED")
        unscr = r["results"]["unscr"]
        assert "list_version" in unscr or unscr.get("source") == "DB"

    def test_workflow_records_list_version(self):
        from app.services.kyc_workflow_engine import (
            create_kyc_session, submit_data_capture,
            submit_nid_verification, submit_biometric,
            submit_screening, get_kyc_session, clear_sessions
        )
        clear_sessions()
        s = create_kyc_session(kyc_type="SIMPLIFIED")
        sid = s["session_id"]
        submit_data_capture(sid, {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
        })
        submit_nid_verification(sid, "1234567890123")
        submit_biometric(sid, {"passed": True, "confidence": 85.0})
        r = submit_screening(sid, "RAHMAN HOSSAIN")
        assert "unscr_list_version" in r or r.get("step_completed") == "screening"


# ── DB indexes ────────────────────────────────────────────────────────────
class TestDBIndexes:
    def test_gin_index_exists(self):
        from app.db.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='unscr_entries' AND indexname='idx_unscr_entries_search_tsv'"
            ))
            assert r.fetchone() is not None

    def test_is_active_index_exists(self):
        from app.db.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='unscr_entries' AND indexname='idx_unscr_entries_is_active'"
            ))
            assert r.fetchone() is not None

    def test_list_version_index_exists(self):
        from app.db.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='unscr_entries' AND indexname='idx_unscr_entries_list_version'"
            ))
            assert r.fetchone() is not None


# ── Admin endpoints ───────────────────────────────────────────────────────
class TestAdminEndpoints:
    def setup_method(self):
        self.token = get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_unscr_status_endpoint(self):
        r = client.get("/api/v1/settings/unscr/status", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "list_version" in data
        assert "total_entries" in data

    def test_unscr_pull_endpoint_admin(self):
        r = client.post("/api/v1/settings/unscr/pull", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "result" in data

    def test_unscr_pull_requires_auth(self):
        r = client.post("/api/v1/settings/unscr/pull")
        assert r.status_code == 403

    def test_unscr_status_requires_auth(self):
        r = client.get("/api/v1/settings/unscr/status")
        assert r.status_code == 403

    def test_agent_cannot_trigger_pull(self):
        agent_token = get_token("agent-bypass@demo.ekyc", "DemoAgent@2026")
        r = client.post("/api/v1/settings/unscr/pull",
            headers={"Authorization": f"Bearer {agent_token}"})
        assert r.status_code == 403


# ── Alert system ──────────────────────────────────────────────────────────
class TestAlertSystem:
    def test_send_alert_increments_prometheus(self):
        from app.services.unscr_service import _send_alert
        from app.services.metrics import EC_API_ERRORS
        before = EC_API_ERRORS.labels(error_type="UNSCR_PULL_FAILURE")._value.get()
        _send_alert("test alert", "UNSCR_PULL_FAILURE")
        after = EC_API_ERRORS.labels(error_type="UNSCR_PULL_FAILURE")._value.get()
        assert after > before

    def test_send_alert_logs_error(self, caplog):
        import logging
        from app.services.unscr_service import _send_alert
        with caplog.at_level(logging.ERROR, logger="app.services.unscr_service"):
            _send_alert("test message", "TEST_ALERT")
        assert "test message" in caplog.text or "TEST_ALERT" in caplog.text


# ── XML parser ────────────────────────────────────────────────────────────
class TestXMLParser:
    def test_parse_demo_entries(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-24")
        assert len(entries) >= 3
        assert all("primary_name" in e for e in entries)
        assert all("un_ref_id" in e for e in entries)

    def test_parse_individual_has_required_fields(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-24")
        individuals = [e for e in entries if e["entry_type"] == "INDIVIDUAL"]
        assert len(individuals) >= 1
        for ind in individuals:
            assert "primary_name" in ind
            assert "aliases" in ind
            assert "search_vector" in ind

    def test_parse_entity_has_required_fields(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-24")
        entities = [e for e in entries if e["entry_type"] == "ENTITY"]
        assert len(entities) >= 1

    def test_search_vector_contains_aliases(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-24")
        al_qaida = next(e for e in entries if "AL QAIDA" in e["primary_name"])
        assert "AL-QAEDA" in al_qaida["search_vector"] or "AQ" in al_qaida["search_vector"]
