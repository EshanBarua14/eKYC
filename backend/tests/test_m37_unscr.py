"""
M37 — UNSCR Live Feed Tests
Daily UN list pull, PostgreSQL storage, FTS search, alert on failure.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════════
# 1. UNSCR DB model
# ══════════════════════════════════════════════════════════════════════════
class TestUNSCRModel:
    def test_unscr_entry_table_exists(self):
        from app.db.database import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        assert "unscr_entries" in inspector.get_table_names()

    def test_unscr_list_meta_table_exists(self):
        from app.db.database import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        assert "unscr_list_meta" in inspector.get_table_names()

    def test_unscr_entry_columns(self):
        from app.db.database import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("unscr_entries")]
        for col in ["id", "un_ref_id", "entry_type", "primary_name",
                    "aliases", "search_vector", "list_version", "is_active"]:
            assert col in cols

    def test_unscr_list_meta_columns(self):
        from app.db.database import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("unscr_list_meta")]
        for col in ["id", "list_version", "total_entries", "status", "pulled_at"]:
            assert col in cols


# ══════════════════════════════════════════════════════════════════════════
# 2. Demo entries
# ══════════════════════════════════════════════════════════════════════════
class TestDemoEntries:
    def test_demo_entries_returns_list(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-20")
        assert isinstance(entries, list)
        assert len(entries) >= 5

    def test_demo_entries_have_required_fields(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-20")
        for e in entries:
            assert "un_ref_id"    in e
            assert "entry_type"   in e
            assert "primary_name" in e
            assert "search_vector" in e

    def test_demo_entries_have_valid_types(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-20")
        types = {e["entry_type"] for e in entries}
        assert types <= {"INDIVIDUAL", "ENTITY"}

    def test_demo_entries_include_al_qaida(self):
        from app.services.unscr_service import _get_demo_entries
        entries = _get_demo_entries("2026-04-20")
        names = [e["primary_name"] for e in entries]
        assert any("AL QAIDA" in n for n in names)


# ══════════════════════════════════════════════════════════════════════════
# 3. List pull
# ══════════════════════════════════════════════════════════════════════════
class TestPullUNList:
    def test_pull_uses_demo_when_url_unreachable(self):
        from app.services.unscr_service import pull_un_list
        with patch("app.services.unscr_service._fetch_and_parse",
                   side_effect=Exception("Network unreachable")):
            result = pull_un_list()
        assert result["status"] == "FAILED"

    def test_pull_with_demo_entries_succeeds(self):
        from app.services.unscr_service import pull_un_list, _get_demo_entries
        demo = _get_demo_entries("2026-04-20")
        with patch("app.services.unscr_service._fetch_and_parse", return_value=demo):
            result = pull_un_list()
        assert result["status"] == "SUCCESS"
        assert result["total_entries"] >= 5

    def test_pull_returns_list_version(self):
        from app.services.unscr_service import pull_un_list, _get_demo_entries
        demo = _get_demo_entries("2026-04-20")
        with patch("app.services.unscr_service._fetch_and_parse", return_value=demo):
            result = pull_un_list()
        assert "list_version" in result

    def test_pull_records_metadata(self):
        from app.services.unscr_service import pull_un_list, _get_demo_entries, get_list_status
        demo = _get_demo_entries("2026-04-20")
        with patch("app.services.unscr_service._fetch_and_parse", return_value=demo):
            pull_un_list()
        status = get_list_status()
        assert status["total_entries"] >= 5

    def test_pull_failure_sends_alert(self):
        from app.services.unscr_service import pull_un_list
        with patch("app.services.unscr_service._fetch_and_parse",
                   side_effect=Exception("timeout")):
            with patch("app.services.unscr_service._send_alert") as mock_alert:
                pull_un_list()
        mock_alert.assert_called_once()

    def test_pull_new_entries_counted(self):
        from app.services.unscr_service import pull_un_list, _get_demo_entries
        demo = _get_demo_entries("test-version-new")
        with patch("app.services.unscr_service._fetch_and_parse", return_value=demo):
            result = pull_un_list()
        assert "new_entries" in result


# ══════════════════════════════════════════════════════════════════════════
# 4. XML parsing
# ══════════════════════════════════════════════════════════════════════════
class TestXMLParsing:
    def test_parse_xml_individual(self):
        from app.services.unscr_service import _parse_xml
        xml = b"""<?xml version="1.0"?>
        <CONSOLIDATED_LIST>
          <INDIVIDUALS>
            <INDIVIDUAL>
              <REFERENCE_NUMBER>QI-001</REFERENCE_NUMBER>
              <FIRST_NAME>JOHN</FIRST_NAME>
              <SECOND_NAME>DOE</SECOND_NAME>
              <UN_LIST_TYPE>1267</UN_LIST_TYPE>
              <LISTED_ON>2001-01-01</LISTED_ON>
            </INDIVIDUAL>
          </INDIVIDUALS>
        </CONSOLIDATED_LIST>"""
        entries = _parse_xml(xml)
        assert len(entries) >= 1
        assert entries[0]["entry_type"] == "INDIVIDUAL"
        assert "JOHN" in entries[0]["primary_name"]

    def test_parse_xml_entity(self):
        from app.services.unscr_service import _parse_xml
        xml = b"""<?xml version="1.0"?>
        <CONSOLIDATED_LIST>
          <ENTITIES>
            <ENTITY>
              <REFERENCE_NUMBER>QE-001</REFERENCE_NUMBER>
              <FIRST_NAME>BAD ORGANIZATION</FIRST_NAME>
              <UN_LIST_TYPE>1267</UN_LIST_TYPE>
              <LISTED_ON>2005-01-01</LISTED_ON>
            </ENTITY>
          </ENTITIES>
        </CONSOLIDATED_LIST>"""
        entries = _parse_xml(xml)
        assert len(entries) >= 1
        assert entries[0]["entry_type"] == "ENTITY"

    def test_parse_xml_empty_returns_empty_list(self):
        from app.services.unscr_service import _parse_xml
        xml = b"""<?xml version="1.0"?><CONSOLIDATED_LIST></CONSOLIDATED_LIST>"""
        entries = _parse_xml(xml)
        assert isinstance(entries, list)

    def test_parse_xml_invalid_returns_empty(self):
        from app.services.unscr_service import _parse_xml
        entries = _parse_xml(b"not xml at all")
        assert isinstance(entries, list)


# ══════════════════════════════════════════════════════════════════════════
# 5. UNSCR search
# ══════════════════════════════════════════════════════════════════════════
class TestSearchUNSCR:
    @pytest.fixture(autouse=True)
    def seed_db(self):
        """Seed DB with demo entries before each test."""
        from app.services.unscr_service import pull_un_list, _get_demo_entries
        demo = _get_demo_entries("test-search-seed")
        with patch("app.services.unscr_service._fetch_and_parse", return_value=demo):
            pull_un_list()

    def test_clear_name_returns_clear(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("CLEAN CITIZEN NORMAL")
        assert result["verdict"] == "CLEAR"

    def test_exact_match_returns_match_or_review(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("AL QAIDA")
        assert result["verdict"] in ("MATCH", "REVIEW")

    def test_known_sanctioned_person_flagged(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("SANCTIONED PERSON ONE")
        assert result["verdict"] in ("MATCH", "REVIEW")
        assert len(result["matches"]) > 0

    def test_result_has_required_fields(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("TEST NAME")
        for field in ["verdict", "name", "matches", "screened_at", "bfiu_ref"]:
            assert field in result

    def test_clear_result_has_empty_matches(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("TOTALLY UNIQUE PERSON XYZ123")
        assert result["verdict"] == "CLEAR"
        assert result["matches"] == []

    def test_match_has_best_score(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("AL QAIDA")
        if result["verdict"] != "CLEAR":
            assert "best_score" in result

    def test_empty_name_returns_clear(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("")
        assert result["verdict"] == "CLEAR"

    def test_bfiu_ref_present(self):
        from app.services.unscr_service import search_unscr
        result = search_unscr("ANY NAME")
        assert "BFIU" in result["bfiu_ref"]


# ══════════════════════════════════════════════════════════════════════════
# 6. List status
# ══════════════════════════════════════════════════════════════════════════
class TestListStatus:
    def test_get_list_status_returns_dict(self):
        from app.services.unscr_service import get_list_status
        status = get_list_status()
        assert isinstance(status, dict)

    def test_get_list_status_has_required_fields(self):
        from app.services.unscr_service import get_list_status
        status = get_list_status()
        for field in ["list_version", "total_entries", "status"]:
            assert field in status

    def test_get_list_status_total_entries_int(self):
        from app.services.unscr_service import get_list_status
        status = get_list_status()
        assert isinstance(status["total_entries"], int)


# ══════════════════════════════════════════════════════════════════════════
# 7. Celery task
# ══════════════════════════════════════════════════════════════════════════
class TestUNSCRCeleryTask:
    @pytest.fixture(autouse=True)
    def eager_celery(self):
        from app.worker.celery_app import celery_app
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        yield
        celery_app.conf.task_always_eager = False

    def test_daily_pull_task_registered(self):
        from app.worker.celery_app import celery_app
        import app.worker.tasks.unscr_pull  # noqa
        assert "app.worker.tasks.unscr_pull.pull_unscr_list_daily" in celery_app.tasks

    def test_daily_pull_task_success(self):
        from app.worker.tasks.unscr_pull import pull_unscr_list_daily
        from app.services.unscr_service import _get_demo_entries
        demo = _get_demo_entries("task-test")
        with patch("app.services.unscr_service._fetch_and_parse", return_value=demo):
            result = pull_unscr_list_daily.apply().get()
        assert result["status"] == "SUCCESS"

    def test_daily_pull_task_in_beat_schedule(self):
        from app.worker.celery_app import celery_app
        assert "unscr-daily-pull" in celery_app.conf.beat_schedule

    def test_helpers_normalize(self):
        from app.services.unscr_service import _normalize
        assert _normalize("al-qaida ") == "AL QAIDA"
        assert _normalize("  test  name  ") == "TEST NAME"

    def test_token_overlap_exact(self):
        from app.services.unscr_service import _token_overlap
        assert _token_overlap("AL QAIDA", "AL QAIDA") == 1.0

    def test_token_overlap_partial(self):
        from app.services.unscr_service import _token_overlap
        score = _token_overlap("AL QAIDA", "AL QAEDA")
        assert 0.0 < score < 1.0

    def test_token_overlap_no_match(self):
        from app.services.unscr_service import _token_overlap
        assert _token_overlap("JOHN SMITH", "AL QAIDA") == 0.0
