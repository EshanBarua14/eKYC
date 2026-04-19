"""
BFIU Report Generation Celery Tasks — M42
Async report generation job triggered by Celery beat monthly.
"""
import logging
from datetime import datetime, timezone
from app.worker.celery_app import celery_app
from app.services.bfiu_report_service import generate_monthly_report

log = logging.getLogger(__name__)


@celery_app.task(
    name="app.worker.tasks.bfiu_report.generate_monthly_report_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def generate_monthly_report_task(
    self,
    year: int = None,
    month: int = None,
    institution_id: str = "default",
    submitted_by: str = "system",
) -> dict:
    """
    Generate BFIU monthly compliance report.
    Defaults to previous month if year/month not specified.
    """
    from app.services.bfiu_report_service import generate_monthly_report

    now = datetime.now(timezone.utc)
    if year is None or month is None:
        month = now.month - 1 or 12
        year  = now.year if now.month > 1 else now.year - 1

    log.info("[M42] Generating BFIU report %d-%02d for %s", year, month, institution_id)

    try:
        result = generate_monthly_report(
            year           = year,
            month          = month,
            institution_id = institution_id,
            submitted_by   = submitted_by,
        )
        log.info("[M42] BFIU report generated: %s", result.get("report_id"))
        return {
            "status":       "generated",
            "report_id":    result.get("report_id"),
            "period":       f"{year}-{month:02d}",
            "generated_at": now.isoformat(),
        }
    except Exception as exc:
        log.error("[M42] BFIU report generation error: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.worker.tasks.bfiu_report.trigger_report_now",
)
def trigger_report_now(year: int, month: int, institution_id: str = "default") -> dict:
    """Manually trigger a BFIU report generation (on-demand)."""
    return generate_monthly_report_task.apply_async(
        kwargs={
            "year":           year,
            "month":          month,
            "institution_id": institution_id,
            "submitted_by":   "manual_trigger",
        }
    ).id
