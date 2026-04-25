"""
M60: Celery tasks for EDD SLA enforcement.
BFIU §4.3: auto-close EDD cases after 1-month SLA.
Add to existing celery_app.py beat schedule.
"""
from celery import shared_task
from app.db.session import SessionLocal
from app.services.edd_service import auto_close_expired_cases, send_sla_warnings
from app.core.timezone import bst_now
import logging

logger = logging.getLogger(__name__)


@shared_task(name="edd.auto_close_expired")
def task_edd_auto_close():
    """
    BFIU §4.3: Auto-close EDD cases past 1-month SLA.
    Run daily at midnight BST.
    """
    db = SessionLocal()
    try:
        closed = auto_close_expired_cases(db)
        logger.info(
            "EDD auto-close completed",
            extra={"closed_count": closed, "bst_time": bst_now().isoformat()}
        )
        return {"closed": closed}
    finally:
        db.close()


@shared_task(name="edd.sla_warnings")
def task_edd_sla_warnings():
    """
    Warn Compliance Officers 7 days before SLA deadline.
    Run daily.
    """
    db = SessionLocal()
    try:
        warned = send_sla_warnings(db, warn_days_before=7)
        logger.info("EDD SLA warnings sent", extra={"count": warned})
        return {"warned": warned}
    finally:
        db.close()


# ─── Add to existing beat schedule in celery_app.py ──────────────────────────
# from celery.schedules import crontab
#
# app.conf.beat_schedule.update({
#     "edd-auto-close-daily": {
#         "task": "edd.auto_close_expired",
#         "schedule": crontab(hour=0, minute=5),  # 00:05 BST daily
#     },
#     "edd-sla-warnings-daily": {
#         "task": "edd.sla_warnings",
#         "schedule": crontab(hour=8, minute=0),  # 08:00 BST daily
#     },
# })
