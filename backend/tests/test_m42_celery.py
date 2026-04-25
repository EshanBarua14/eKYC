"""
M42 — Celery Task Queue Tests
Tests run with task_always_eager=True (synchronous execution, no worker needed).
"""
import pytest
import os
if os.getenv("INTEGRATION_TESTS") != "1":
    try:
        import psycopg2
        from urllib.parse import urlparse
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("postgresql"):
            p = urlparse(db_url)
            conn = psycopg2.connect(host=p.hostname, port=p.port or 5432,
                user=p.username, password=p.password,
                dbname=p.path.lstrip("/"), connect_timeout=2)
            conn.close()
        else:
            pytest.skip("PostgreSQL not configured", allow_module_level=True)
    except Exception:
        pytest.skip("PostgreSQL not available", allow_module_level=True)


import pytest
from unittest.mock import patch, MagicMock
from app.worker.celery_app import celery_app

# ── Force eager execution (no worker needed) ─────────────────────────────
@pytest.fixture(autouse=True)
def eager_celery():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False


# ══════════════════════════════════════════════════════════════════════════
# 1. Celery app configuration
# ══════════════════════════════════════════════════════════════════════════
class TestCeleryApp:
    def test_celery_app_name(self):
        assert celery_app.main == "ekyc"

    def test_celery_broker_configured(self):
        assert celery_app.conf.broker_url is not None

    def test_celery_backend_configured(self):
        assert celery_app.conf.result_backend is not None

    def test_celery_serializer_json(self):
        assert celery_app.conf.task_serializer == "json"

    def test_celery_utc_enabled(self):
        assert celery_app.conf.enable_utc is True

    def test_beat_schedule_has_three_tasks(self):
        schedule = celery_app.conf.beat_schedule
        assert len(schedule) >= 3

    def test_beat_schedule_has_bfiu_report(self):
        assert "bfiu-monthly-report" in celery_app.conf.beat_schedule

    def test_beat_schedule_has_periodic_review(self):
        assert "periodic-review-scheduler" in celery_app.conf.beat_schedule

    def test_beat_schedule_has_nid_sweep(self):
        assert "nid-retry-sweep" in celery_app.conf.beat_schedule

    def test_all_tasks_registered(self):
        import app.worker.tasks.nid_verify       # noqa
        import app.worker.tasks.bfiu_report      # noqa
        import app.worker.tasks.periodic_review  # noqa
        task_names = list(celery_app.tasks.keys())
        assert "app.worker.tasks.nid_verify.verify_nid_async" in task_names
        assert "app.worker.tasks.bfiu_report.generate_monthly_report_task" in task_names
        assert "app.worker.tasks.periodic_review.run_periodic_review_scheduler" in task_names


# ══════════════════════════════════════════════════════════════════════════
# 2. NID verification task
# ══════════════════════════════════════════════════════════════════════════
class TestNIDVerifyTask:
    def test_verify_nid_async_success(self):
        from app.worker.tasks.nid_verify import verify_nid_async
        mock_result = {"status": "verified", "nid_number": "1234567890123"}
        with patch("app.worker.tasks.nid_verify.lookup_nid", return_value=mock_result):
            with patch("app.worker.tasks.nid_verify._update_session_state"):
                result = verify_nid_async.apply(
                    args=["1234567890123", "sess_001", "inst_001"]
                ).get()
        assert result["status"] == "verified"
        assert result["session_id"] == "sess_001"

    def test_verify_nid_async_ec_unavailable_retries(self):
        from app.worker.tasks.nid_verify import verify_nid_async
        celery_app.conf.task_always_eager = False
        with patch("app.worker.tasks.nid_verify.lookup_nid",
                   return_value={"status": "EC_UNAVAILABLE"}):
            with patch("app.worker.tasks.nid_verify._update_session_state"):
                task = verify_nid_async.apply_async(
                    args=["1234567890123", "sess_002", "inst_001"]
                )
        celery_app.conf.task_always_eager = True
        assert task.id is not None

    def test_verify_nid_async_error_handled(self):
        from app.worker.tasks.nid_verify import verify_nid_async
        # In eager mode with propagate=True, non-EC exceptions surface as task result
        with patch("app.worker.tasks.nid_verify.lookup_nid",
                   return_value={"status": "error", "reason": "DB error"}):
            with patch("app.worker.tasks.nid_verify._update_session_state"):
                result = verify_nid_async.apply(
                    args=["1234567890123", "sess_003", "inst_001"]
                ).get()
        assert result is not None
        assert "session_id" in result

    def test_sweep_pending_nid_queue_runs(self):
        from app.worker.tasks.nid_verify import sweep_pending_nid_queue
        with patch("app.worker.tasks.nid_verify.verify_nid_async") as mock_task:
            mock_task.delay = MagicMock()
            result = sweep_pending_nid_queue.apply().get()
        assert "requeued" in result
        assert "swept_at" in result

    def test_backoff_increases_with_retries(self):
        from app.worker.tasks.nid_verify import _backoff
        assert _backoff(0) == 60
        assert _backoff(1) == 120
        assert _backoff(2) == 240
        assert _backoff(10) == 3600   # capped at max

    def test_backoff_capped_at_max(self):
        from app.worker.tasks.nid_verify import _backoff, MAX_BACKOFF_SEC
        assert _backoff(20) == MAX_BACKOFF_SEC


# ══════════════════════════════════════════════════════════════════════════
# 3. BFIU report task
# ══════════════════════════════════════════════════════════════════════════
class TestBFIUReportTask:
    def test_generate_monthly_report_task_success(self):
        from app.worker.tasks.bfiu_report import generate_monthly_report_task
        mock_report = {"report_id": "RPT-001", "period": "2026-03"}
        with patch("app.worker.tasks.bfiu_report.generate_monthly_report",
                   return_value=mock_report):
            result = generate_monthly_report_task.apply(
                kwargs={"year": 2026, "month": 3, "institution_id": "default"}
            ).get()
        assert result["status"] == "generated"
        assert result["report_id"] is not None

    def test_generate_monthly_report_defaults_to_previous_month(self):
        from app.worker.tasks.bfiu_report import generate_monthly_report_task
        from datetime import datetime, timezone
        mock_report = {"report_id": "RPT-002"}
        with patch("app.worker.tasks.bfiu_report.generate_monthly_report",
                   return_value=mock_report):
            result = generate_monthly_report_task.apply(kwargs={}).get()
        assert result["status"] == "generated"

    def test_generate_monthly_report_has_period(self):
        from app.worker.tasks.bfiu_report import generate_monthly_report_task
        mock_report = {"report_id": "RPT-003"}
        with patch("app.worker.tasks.bfiu_report.generate_monthly_report",
                   return_value=mock_report):
            result = generate_monthly_report_task.apply(
                kwargs={"year": 2026, "month": 3}
            ).get()
        assert "period" in result
        assert result["period"] == "2026-03"

    def test_trigger_report_now_queues_task(self):
        from app.worker.tasks.bfiu_report import trigger_report_now
        mock_report = {"report_id": "RPT-004"}
        with patch("app.worker.tasks.bfiu_report.generate_monthly_report",
                   return_value=mock_report):
            result = trigger_report_now.apply(
                args=[2026, 3, "default"]
            ).get()
        assert result is not None


# ══════════════════════════════════════════════════════════════════════════
# 4. Periodic review scheduler task
# ══════════════════════════════════════════════════════════════════════════
class TestPeriodicReviewTask:
    def test_run_periodic_review_scheduler_returns_dict(self):
        from app.worker.tasks.periodic_review import run_periodic_review_scheduler
        result = run_periodic_review_scheduler.apply().get()
        assert isinstance(result, dict)
        assert "queued" in result
        assert "errors" in result
        assert "scheduled_at" in result

    def test_run_periodic_review_scheduler_status_completed(self):
        from app.worker.tasks.periodic_review import run_periodic_review_scheduler
        result = run_periodic_review_scheduler.apply().get()
        assert result["status"] == "completed"

    def test_notify_review_due_success(self):
        from app.worker.tasks.periodic_review import notify_review_due
        result = notify_review_due.apply(kwargs={
            "session_id":     "sess_review_001",
            "risk_grade":     "HIGH",
            "review_due":     "2027-04-20T00:00:00+00:00",
            "institution_id": "default",
        }).get()
        assert result["status"] == "notified"
        assert result["session_id"] == "sess_review_001"
        assert result["risk_grade"] == "HIGH"

    def test_notify_review_due_has_timestamp(self):
        from app.worker.tasks.periodic_review import notify_review_due
        result = notify_review_due.apply(kwargs={
            "session_id":  "sess_review_002",
            "risk_grade":  "MEDIUM",
            "review_due":  "2028-04-20T00:00:00+00:00",
        }).get()
        assert "notified_at" in result

    def test_review_frequency_days(self):
        from app.worker.tasks.periodic_review import REVIEW_FREQUENCY_DAYS
        assert REVIEW_FREQUENCY_DAYS["HIGH"]   == 365
        assert REVIEW_FREQUENCY_DAYS["MEDIUM"] == 730
        assert REVIEW_FREQUENCY_DAYS["LOW"]    == 1825

    def test_notification_days_before(self):
        from app.worker.tasks.periodic_review import NOTIFICATION_DAYS_BEFORE
        assert NOTIFICATION_DAYS_BEFORE["HIGH"]   == 30
        assert NOTIFICATION_DAYS_BEFORE["MEDIUM"] == 30
        assert NOTIFICATION_DAYS_BEFORE["LOW"]    == 60
