"""M53 — Adverse Media Daily Re-screening Tests — BFIU §5.3"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ── Unit: screen_adverse_media ────────────────────────────────────────────
def test_adverse_media_clear():
    from app.services.screening_service import screen_adverse_media
    r = screen_adverse_media("NORMAL PERSON BD", "REGULAR")
    assert r["verdict"] == "CLEAR"
    assert r["hit_count"] == 0
    assert r["edd_required"] is False
    assert "bfiu_ref" in r

def test_adverse_media_flagged():
    from app.services.screening_service import screen_adverse_media
    from unittest.mock import patch
    mock_result = {"verdict": "FLAGGED", "hit_count": 3, "edd_required": True,
                   "sources": ["mock"], "hits": [{"headline": "fraud", "score": 0.9}],
                   "screened_at": "2026-04-27", "bfiu_ref": "BFIU Circular No. 29 s5.3",
                   "name": "KARIM CORRUPT", "kyc_type": "REGULAR"}
    with patch("app.services.adverse_media_service.screen_adverse_media_live",
               return_value=mock_result):
        r = screen_adverse_media("KARIM CORRUPT", "REGULAR")
    assert r["verdict"] == "FLAGGED"
    assert r["hit_count"] > 0
    assert r["edd_required"] is True

def test_adverse_media_simplified_still_screens():
    from app.services.screening_service import screen_adverse_media
    from unittest.mock import patch
    mock_result = {"verdict": "FLAGGED", "hit_count": 3, "edd_required": True,
                   "sources": ["mock"], "hits": [{"headline": "fraud", "score": 0.9}],
                   "screened_at": "2026-04-27", "bfiu_ref": "BFIU Circular No. 29 s5.3",
                   "name": "KARIM CORRUPT", "kyc_type": "SIMPLIFIED"}
    with patch("app.services.adverse_media_service.screen_adverse_media_live",
               return_value=mock_result):
        r = screen_adverse_media("KARIM CORRUPT", "SIMPLIFIED")
    assert r["verdict"] == "FLAGGED"


# ── Unit: Celery task logic (mocked DB) ───────────────────────────────────
def test_rescan_task_completes():
    from app.worker.tasks.adverse_media_rescan import run_adverse_media_rescan

    mock_profile = MagicMock()
    mock_profile.status       = "APPROVED"
    mock_profile.full_name    = "NORMAL PERSON BD"
    mock_profile.kyc_type     = "REGULAR"
    mock_profile.session_id   = "sess-test-001"
    mock_profile.adverse_media_flag = False

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_profile]

    with patch("app.db.database.db_session") as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: mock_db
        mock_ctx.return_value.__exit__  = lambda s,*a: False
        result = run_adverse_media_rescan.run()

    assert result["status"]   == "completed"
    assert result["screened"] == 1
    assert result["errors"]   == 0
    assert "bfiu_ref" in result

def test_rescan_task_flags_and_sets_edd():
    from app.worker.tasks.adverse_media_rescan import run_adverse_media_rescan
    mock_profile = MagicMock()
    mock_profile.status            = "APPROVED"
    mock_profile.full_name         = "KARIM CORRUPT"
    mock_profile.kyc_type          = "REGULAR"
    mock_profile.session_id        = "sess-test-002"
    mock_profile.adverse_media_flag = False
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_profile]
    mock_screen = {
        "verdict": "FLAGGED", "hit_count": 2, "edd_required": True,
        "hits": [{"headline": "fraud case"}], "sources": ["mock"],
        "screened_at": "2026-04-27", "bfiu_ref": "BFIU s5.3",
        "name": "KARIM CORRUPT", "kyc_type": "REGULAR",
    }
    with patch("app.db.database.db_session") as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: mock_db
        mock_ctx.return_value.__exit__  = lambda s,*a: False
        with patch("app.services.screening_service.screen_adverse_media",
                   return_value=mock_screen):
            result = run_adverse_media_rescan.run()
    assert result["flagged"] >= 1
    assert mock_profile.edd_required is True
    assert mock_profile.adverse_media_flag is True


def test_rescan_skips_empty_name():
    from app.worker.tasks.adverse_media_rescan import run_adverse_media_rescan

    mock_profile = MagicMock()
    mock_profile.status     = "APPROVED"
    mock_profile.full_name  = ""
    mock_profile.session_id = "sess-test-003"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_profile]

    with patch("app.db.database.db_session") as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: mock_db
        mock_ctx.return_value.__exit__  = lambda s,*a: False
        result = run_adverse_media_rescan.run()

    assert result["screened"] == 0


# ── Beat schedule wired ───────────────────────────────────────────────────
def test_beat_schedule_contains_adverse_rescan():
    from app.worker.celery_app import celery_app
    assert "adverse-media-rescan" in celery_app.conf.beat_schedule
    task = celery_app.conf.beat_schedule["adverse-media-rescan"]
    assert task["task"] == "app.worker.tasks.adverse_media_rescan.run_adverse_media_rescan"

def test_task_importable():
    from app.worker.tasks.adverse_media_rescan import run_adverse_media_rescan
    assert callable(run_adverse_media_rescan)
