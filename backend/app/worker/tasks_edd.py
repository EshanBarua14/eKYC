"""M60: Celery tasks — EDD SLA enforcement. BFIU §4.3."""
from celery import shared_task
from app.db.database import SessionLocal
from app.services.edd_service import auto_close_expired_cases, send_sla_warnings
from app.core.timezone import now_bst as bst_now
import logging
logger = logging.getLogger(__name__)

@shared_task(name="edd.auto_close_expired")
def task_edd_auto_close():
    """BFIU §4.3: auto-close EDD cases past 1-month SLA. Run daily 00:05 BST."""
    db = SessionLocal()
    try:
        closed = auto_close_expired_cases(db)
        logger.info("EDD auto-close", extra={"closed": closed, "bst": bst_now().isoformat()})
        return {"closed": closed}
    finally:
        db.close()

@shared_task(name="edd.sla_warnings")
def task_edd_sla_warnings():
    """Warn CO 7 days before SLA deadline. Run daily 08:00 BST."""
    db = SessionLocal()
    try:
        warned = send_sla_warnings(db, warn_days_before=7)
        logger.info("EDD SLA warnings", extra={"count": warned})
        return {"warned": warned}
    finally:
        db.close()
