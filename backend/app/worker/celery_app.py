"""
Celery Application — M42
Broker: Redis. Backend: Redis.
Auto-fallback warning if Redis unavailable.
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BROKER_URL  = os.getenv("CELERY_BROKER_URL",  REDIS_URL)
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

celery_app = Celery(
    "ekyc",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=[
        "app.worker.tasks.nid_verify",
        "app.worker.tasks.bfiu_report",
        "app.worker.tasks.periodic_review",
        "app.worker.tasks.unscr_pull",
    ],
)

celery_app.conf.update(
    task_serializer          = "json",
    result_serializer        = "json",
    accept_content           = ["json"],
    timezone                 = "UTC",
    enable_utc               = True,
    task_track_started       = True,
    task_acks_late           = True,
    worker_prefetch_multiplier = 1,
    result_expires           = 86400,   # 24 hours
    task_soft_time_limit     = 300,     # 5 min soft
    task_time_limit          = 600,     # 10 min hard
)

# ── Celery Beat schedule (M42) ────────────────────────────────────────────
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # BFIU monthly report — 1st of every month at 01:00 UTC
    "bfiu-monthly-report": {
        "task":     "app.worker.tasks.bfiu_report.generate_monthly_report_task",
        "schedule": crontab(hour=1, minute=0, day_of_month=1),
        "kwargs":   {"institution_id": "default", "submitted_by": "system"},
    },
    # Periodic review scheduler — daily at 02:00 UTC
    "periodic-review-scheduler": {
        "task":     "app.worker.tasks.periodic_review.run_periodic_review_scheduler",
        "schedule": crontab(hour=2, minute=0),
    },
    # NID retry queue sweep — every 15 minutes
    "nid-retry-sweep": {
        "task":     "app.worker.tasks.nid_verify.sweep_pending_nid_queue",
        "schedule": crontab(minute="*/15"),
    },
    # UNSCR daily list pull — every day at 00:30 UTC
    "unscr-daily-pull": {
        "task":     "app.worker.tasks.unscr_pull.pull_unscr_list_daily",
        "schedule": crontab(hour=0, minute=30),
    },
}
