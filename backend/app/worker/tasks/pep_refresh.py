"""
M103 -- OpenSanctions PEP Daily Refresh Task -- BFIU Circular No. 29 s4.2
Celery beat: daily at 04:00 UTC (10:00 BST)
Sources: OpenSanctions BD PEPs + UN SC Sanctions + OFAC SDN + EU FSF
"""
import logging
from app.worker.celery_app import celery_app
from app.db.database import db_session

log = logging.getLogger(__name__)


@celery_app.task(
    name="pep.daily_refresh",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,  # retry after 1 hour on failure
    soft_time_limit=600,
    time_limit=900,
)
def refresh_pep_list_daily(self, limit: int = 0):
    """
    Fetch fresh PEP data from OpenSanctions and load into DB.
    BFIU s4.2: PEP list must be kept current.
    """
    log.info("[M103] Starting daily PEP refresh (BFIU s4.2)")
    try:
        from app.scripts.fetch_opensanctions_pep import fetch_and_load
        with db_session() as db:
            stats = fetch_and_load(db, limit=limit)
        log.info("[M103] PEP refresh complete: %s", stats)
        return {
            "status": "ok",
            "stats": stats,
            "bfiu_ref": "BFIU Circular No. 29 s4.2",
        }
    except Exception as exc:
        log.error("[M103] PEP refresh failed: %s", exc)
        raise self.retry(exc=exc)
