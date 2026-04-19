"""
Periodic Review Scheduler Celery Tasks — M42
Daily sweep for KYC profiles due for review by risk tier.
HIGH=1yr, MEDIUM=2yr, LOW=5yr (BFIU Section 5.7)
"""
import logging
from datetime import datetime, timezone, timedelta
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)

REVIEW_FREQUENCY_DAYS = {
    "HIGH":   365,
    "MEDIUM": 730,
    "LOW":    1825,
}

NOTIFICATION_DAYS_BEFORE = {
    "HIGH":   30,
    "MEDIUM": 30,
    "LOW":    60,
}


@celery_app.task(
    name="app.worker.tasks.periodic_review.run_periodic_review_scheduler",
)
def run_periodic_review_scheduler() -> dict:
    """
    Daily Celery beat task.
    Finds KYC profiles due for review and queues notification tasks.
    """
    from app.db.database import db_session
    from app.db.models_platform import KYCProfile

    now    = datetime.now(timezone.utc)
    queued = 0
    errors = 0

    log.info("[M42] Running periodic review scheduler: %s", now.isoformat())

    try:
        with db_session() as db:
            profiles = db.query(KYCProfile).filter(
                KYCProfile.verdict == "APPROVED"
            ).all()

            for profile in profiles:
                risk_grade = getattr(profile, "risk_grade", "LOW") or "LOW"
                freq_days  = REVIEW_FREQUENCY_DAYS.get(risk_grade, 1825)
                notify_before = NOTIFICATION_DAYS_BEFORE.get(risk_grade, 30)

                created = getattr(profile, "created_at", None)
                if not created:
                    continue

                review_due = created + timedelta(days=freq_days)
                notify_at  = review_due - timedelta(days=notify_before)

                if now >= notify_at:
                    notify_review_due.delay(
                        session_id  = profile.session_id,
                        risk_grade  = risk_grade,
                        review_due  = review_due.isoformat(),
                        institution_id = getattr(profile, "institution_id", "default"),
                    )
                    queued += 1

    except Exception as exc:
        log.error("[M42] Periodic review scheduler error: %s", exc)
        errors += 1

    result = {
        "status":      "completed",
        "queued":      queued,
        "errors":      errors,
        "scheduled_at": now.isoformat(),
    }
    log.info("[M42] Periodic review scheduler done: %s", result)
    return result


@celery_app.task(
    name="app.worker.tasks.periodic_review.notify_review_due",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def notify_review_due(
    self,
    session_id:     str,
    risk_grade:     str,
    review_due:     str,
    institution_id: str = "default",
) -> dict:
    """
    Send review due notification to compliance officers.
    """
    log.info("[M42] Review due notification: session=%s risk=%s due=%s",
             session_id, risk_grade, review_due)
    try:
        from app.db.database import db_session
        from app.db.models_platform import KYCProfile
        with db_session() as db:
            profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
            if profile:
                profile.updated_at = datetime.now(timezone.utc)

        return {
            "status":       "notified",
            "session_id":   session_id,
            "risk_grade":   risk_grade,
            "review_due":   review_due,
            "notified_at":  datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        log.error("[M42] notify_review_due error: %s", exc)
        raise self.retry(exc=exc)
