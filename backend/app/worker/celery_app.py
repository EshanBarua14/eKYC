"""Celery Application -- M42"""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
load_dotenv()

REDIS_URL   = os.getenv("REDIS_URL",   "redis://localhost:6379/0")
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
        "app.worker.tasks.adverse_media_rescan",
        "app.worker.tasks.pep_refresh",
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
    result_expires           = 86400,
    task_soft_time_limit     = 300,
    task_time_limit          = 600,
)

celery_app.conf.beat_schedule = {
    # BFIU monthly report -- 1st of every month at 01:00 UTC
    "bfiu-monthly-report": {
        "task":     "app.worker.tasks.bfiu_report.generate_monthly_report_task",
        "schedule": crontab(hour=1, minute=0, day_of_month=1),
        "kwargs":   {"institution_id": "default", "submitted_by": "system"},
    },
    # Periodic review scheduler -- daily at 02:00 UTC
    "periodic-review-scheduler": {
        "task":     "app.worker.tasks.periodic_review.run_periodic_review_scheduler",
        "schedule": crontab(hour=2, minute=0),
    },
    # NID retry queue sweep -- every 15 minutes
    "nid-retry-sweep": {
        "task":     "app.worker.tasks.nid_verify.sweep_pending_nid_queue",
        "schedule": crontab(minute="*/15"),
    },
    # UNSCR daily list pull -- every day at 00:30 UTC
    "unscr-daily-pull": {
        "task":     "app.worker.tasks.unscr_pull.pull_unscr_list_daily",
        "schedule": crontab(hour=0, minute=30),
    },
    # M53 Adverse media daily re-screening -- BFIU s5.3 -- 03:00 UTC
    "adverse-media-rescan": {
        "task":     "app.worker.tasks.adverse_media_rescan.run_adverse_media_rescan",
        "schedule": crontab(hour=3, minute=0),
    },
    # M103 OpenSanctions PEP daily refresh -- BFIU s4.2 -- 04:00 UTC (10:00 BST)
    "pep-daily-refresh": {
        "task":     "pep.daily_refresh",
        "schedule": crontab(hour=4, minute=0),
        "kwargs":   {"limit": 0},
    },
}

# M60: EDD SLA enforcement (BFIU s4.3)
from app.worker.tasks_edd import task_edd_auto_close, task_edd_sla_warnings  # noqa
celery_app.conf.beat_schedule.update({
    "edd-auto-close-daily":   {"task": "edd.auto_close_expired",  "schedule": crontab(hour=0, minute=5)},
    "edd-sla-warnings-daily": {"task": "edd.sla_warnings",         "schedule": crontab(hour=8, minute=0)},
})

# M67: 5-year retention check (BFIU s5.1) -- monthly
from app.worker.tasks_retention import task_flag_retention_eligible  # noqa
celery_app.conf.beat_schedule.update({
    "retention-monthly-check": {
        "task":     "retention.flag_eligible_records",
        "schedule": crontab(hour=1, minute=0, day_of_month=1),
    },
})
