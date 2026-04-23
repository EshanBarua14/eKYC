"""
M53 — Adverse Media Daily Re-screening — BFIU Circular No. 29 §5.3
Daily Celery beat task.
Re-screens all APPROVED KYC profiles for adverse media hits.
On new flag: sets edd_required=True, logs audit event.
"""
import logging
import uuid
from datetime import datetime, timezone

from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(
    name="app.worker.tasks.adverse_media_rescan.run_adverse_media_rescan",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,
)
def run_adverse_media_rescan(self) -> dict:
    """
    Daily sweep: re-screen all APPROVED profiles for adverse media.
    BFIU §5.3: ongoing monitoring, not just at onboarding.
    """
    from app.db.database import db_session
    from app.db.models_platform import KYCProfile, AuditLog
    from app.services.screening_service import screen_adverse_media

    now      = datetime.now(timezone.utc)
    screened = flagged = errors = 0

    log.info("[M53] Adverse media re-screening starting: %s", now.isoformat())

    try:
        with db_session() as db:
            profiles = db.query(KYCProfile).filter(
                KYCProfile.status == "APPROVED"
            ).all()

            for profile in profiles:
                try:
                    name     = getattr(profile, "full_name", "") or ""
                    kyc_type = getattr(profile, "kyc_type",  "REGULAR") or "REGULAR"
                    if not name:
                        continue

                    result = screen_adverse_media(name, kyc_type)
                    screened += 1

                    was_flagged = bool(getattr(profile, "adverse_media_flag", False))
                    now_flagged = result["verdict"] == "FLAGGED"

                    profile.adverse_media_checked    = True
                    profile.adverse_media_flag       = now_flagged
                    profile.adverse_media_checked_at = now
                    profile.adverse_media_hits       = result.get("hits", [])

                    if now_flagged:
                        flagged += 1
                        profile.edd_required = True
                        # Audit only on new flags (avoid log spam on repeat runs)
                        if not was_flagged:
                            db.add(AuditLog(
                                id           = str(uuid.uuid4()),
                                event_type   = "ADVERSE_MEDIA_FLAG",
                                entity_type  = "kyc_profile",
                                entity_id    = profile.session_id,
                                actor_id     = "celery_beat_m53",
                                actor_role   = "SYSTEM",
                                session_id   = profile.session_id,
                                after_state  = {
                                    "verdict":   result["verdict"],
                                    "hit_count": result["hit_count"],
                                    "hits":      result.get("hits", []),
                                },
                                bfiu_ref     = "BFIU Circular No. 29 - Section 5.3",
                                retention_until = datetime(2031, 12, 31, tzinfo=timezone.utc),
                                timestamp    = now,
                            ))
                            log.warning(
                                "[M53] NEW adverse media flag: session=%s name=%s hits=%d",
                                profile.session_id, name, result["hit_count"],
                            )

                except Exception as profile_err:
                    log.error("[M53] Error screening session=%s: %s",
                              getattr(profile, "session_id", "?"), profile_err)
                    errors += 1

            db.commit()

    except Exception as exc:
        log.error("[M53] Fatal error in adverse media rescan: %s", exc)
        raise self.retry(exc=exc, countdown=3600)

    result = {
        "status":     "completed",
        "screened":   screened,
        "flagged":    flagged,
        "errors":     errors,
        "run_at":     now.isoformat(),
        "bfiu_ref":   "BFIU Circular No. 29 - Section 5.3",
    }
    log.info("[M53] Adverse media rescan done: %s", result)
    return result
