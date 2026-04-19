"""
NID Verification Celery Tasks — M42
Async NID verification queue with exponential backoff (max 6hrs).
Handles EC API downtime via pending_verification state.
"""
import logging
from datetime import datetime, timezone
from celery import shared_task
from celery.utils.log import get_task_logger
from app.worker.celery_app import celery_app
from app.services.nid_api_client import lookup_nid

log = get_task_logger(__name__)

MAX_RETRIES      = 12          # 12 retries over ~6 hours
BASE_BACKOFF_SEC = 60          # 1 min base
MAX_BACKOFF_SEC  = 3600        # 1 hour cap


def _backoff(retries: int) -> int:
    """Exponential backoff: 60s, 120s, 240s … capped at 3600s."""
    return min(BASE_BACKOFF_SEC * (2 ** retries), MAX_BACKOFF_SEC)


@celery_app.task(
    bind=True,
    name="app.worker.tasks.nid_verify.verify_nid_async",
    max_retries=MAX_RETRIES,
    default_retry_delay=BASE_BACKOFF_SEC,
    acks_late=True,
)
def verify_nid_async(self, nid_number: str, session_id: str, institution_id: str) -> dict:
    """
    Async NID verification via EC API.
    Retries with exponential backoff for up to 6 hours on EC downtime.
    """
    from app.services.nid_api_client import lookup_nid
    try:
        log.info("[M42] NID verify task: session=%s attempt=%d", session_id, self.request.retries)
        result = lookup_nid(nid_number)

        if result.get("status") == "EC_UNAVAILABLE":
            delay = _backoff(self.request.retries)
            log.warning("[M42] EC unavailable — retrying in %ds (attempt %d/%d)",
                        delay, self.request.retries + 1, MAX_RETRIES)
            raise self.retry(countdown=delay)

        _update_session_state(session_id, "verified", result)
        log.info("[M42] NID verify success: session=%s", session_id)
        return {"status": "verified", "session_id": session_id, "result": result}

    except self.MaxRetriesExceededError:
        log.error("[M42] NID verify max retries exceeded: session=%s", session_id)
        _update_session_state(session_id, "pending_verification", {"reason": "EC_TIMEOUT"})
        return {"status": "pending_verification", "session_id": session_id}

    except Exception as exc:
        if "EC_UNAVAILABLE" not in str(exc):
            log.error("[M42] NID verify unexpected error: %s", exc)
            _update_session_state(session_id, "error", {"reason": str(exc)})
            return {"status": "error", "session_id": session_id, "error": str(exc)}
        delay = _backoff(self.request.retries)
        raise self.retry(exc=exc, countdown=delay)


@celery_app.task(
    name="app.worker.tasks.nid_verify.sweep_pending_nid_queue",
)
def sweep_pending_nid_queue() -> dict:
    """
    Celery beat task — sweep sessions stuck in pending_verification state.
    Re-queues them for retry if within 6hr window.
    """
    from app.db.database import db_session
    from app.db.models_platform import KYCProfile
    from datetime import timedelta

    log.info("[M42] Sweeping pending NID verification queue")
    now     = datetime.now(timezone.utc)
    cutoff  = now - timedelta(hours=6)
    requeued = 0

    try:
        with db_session() as db:
            pending = db.query(KYCProfile).filter(
                KYCProfile.verdict == "pending_verification"
            ).all()

            for profile in pending:
                if profile.created_at and profile.created_at >= cutoff:
                    verify_nid_async.delay(
                        nid_number     = profile.session_id,
                        session_id     = profile.session_id,
                        institution_id = profile.institution_id or "default",
                    )
                    requeued += 1

        log.info("[M42] Requeued %d pending NID verifications", requeued)
    except Exception as exc:
        log.error("[M42] Sweep error: %s", exc)

    return {"requeued": requeued, "swept_at": now.isoformat()}


def _update_session_state(session_id: str, state: str, data: dict) -> None:
    """Update KYCProfile verdict/state in DB."""
    try:
        from app.db.database import db_session
        from app.db.models_platform import KYCProfile
        with db_session() as db:
            profile = db.query(KYCProfile).filter_by(session_id=session_id).first()
            if profile:
                profile.verdict    = state
                profile.updated_at = datetime.now(timezone.utc)
    except Exception as exc:
        log.warning("[M42] _update_session_state error: %s", exc)
