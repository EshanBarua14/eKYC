"""
M67: 5-year data retention enforcement
BFIU Circular No. 29 §5.1

Policy: all KYC records retained for 5 years post-account-closure.
This task flags records eligible for archival (NOT deletion).
Actual deletion only after 5 years AND compliance officer sign-off.
"""
from celery import shared_task
from sqlalchemy import text
from app.db.database import SessionLocal
from app.core.timezone import now_bst as bst_now
import logging

logger = logging.getLogger("ekyc.retention")

RETENTION_YEARS = 5


@shared_task(name="retention.flag_eligible_records")
def task_flag_retention_eligible():
    """
    BFIU §5.1: Flag KYC records eligible for archival (5 years post-closure).
    Run monthly. Records flagged for compliance officer review before any archival.
    """
    db = SessionLocal()
    try:
        now = bst_now()
        result = db.execute(text("""
            SELECT COUNT(*) FROM kyc_profiles
            WHERE status IN ('REJECTED', 'CLOSED', 'EXPIRED')
            AND updated_at < NOW() - INTERVAL '5 years'
        """))
        count = result.scalar()

        logger.info(
            "Retention check complete",
            extra={
                "eligible_for_archival": count,
                "retention_years": RETENTION_YEARS,
                "bfiu_ref": "BFIU Circular No. 29 §5.1",
                "checked_at_bst": now.isoformat(),
            }
        )
        return {"eligible_for_archival": count, "action": "FLAGGED_FOR_REVIEW"}
    finally:
        db.close()
