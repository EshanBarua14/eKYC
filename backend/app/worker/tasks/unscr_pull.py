"""
UNSCR Daily Pull Celery Task — M37
Scheduled daily via Celery beat.
Alerts on failure, retries on transient errors.
"""
import logging
from datetime import datetime, timezone
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(
    name="app.worker.tasks.unscr_pull.pull_unscr_list_daily",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,   # retry after 1hr on failure
)
def pull_unscr_list_daily(self) -> dict:
    """
    Daily Celery beat task — pull UN consolidated sanctions list.
    Retries up to 3 times (3hr window) on failure.
    Sends alert if all retries exhausted.
    """
    from app.services.unscr_service import pull_un_list

    log.info("[M37] Daily UN list pull starting")
    try:
        result = pull_un_list(pulled_by="celery_beat_daily")

        if result["status"] == "FAILED":
            log.error("[M37] UN list pull failed: %s", result.get("error"))
            raise self.retry(countdown=3600)

        log.info("[M37] Daily UN list pull complete: %s entries", result.get("total_entries"))
        return result

    except self.MaxRetriesExceededError:
        log.error("[M37] UN list pull max retries exceeded — manual intervention required")
        from app.services.unscr_service import _send_alert
        _send_alert("UN list daily pull FAILED after 3 retries — manual intervention required")
        return {
            "status":   "FAILED_PERMANENT",
            "message":  "Max retries exceeded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        log.error("[M37] Unexpected error in UN list pull: %s", exc)
        raise self.retry(exc=exc, countdown=3600)
