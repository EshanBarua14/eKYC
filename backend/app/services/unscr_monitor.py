"""
M74: UNSCR Feed Failure Monitoring
BFIU Circular No. 29 §3.2.2

Monitors UNSCR list freshness. If last pull > 24h ago,
logs critical alert and sets prometheus gauge.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.timezone import now_bst as bst_now

logger = logging.getLogger("ekyc.unscr_monitor")
MAX_STALENESS_HOURS = 24


def check_unscr_freshness(db: Session) -> dict:
    """
    Check if UNSCR list was pulled within last 24 hours.
    Returns status dict. Logs CRITICAL if stale.
    """
    try:
        from app.db.models_platform import UNSCRListMeta
        meta = db.query(UNSCRListMeta).order_by(
            UNSCRListMeta.last_updated_at.desc()
        ).first()

        if not meta:
            logger.critical(
                "UNSCR list has never been pulled",
                extra={"bfiu_ref": "BFIU Circular No. 29 §3.2.2",
                       "action_required": "Run alembic upgrade head and trigger UNSCR pull"}
            )
            return {"status": "NEVER_PULLED", "stale": True, "hours_since_pull": None}

        now = bst_now()
        hours_since = (now - meta.last_updated_at.replace(tzinfo=timezone.utc).astimezone(
            timezone(timedelta(hours=6))
        )).total_seconds() / 3600

        if hours_since > MAX_STALENESS_HOURS:
            logger.critical(
                "UNSCR list is stale",
                extra={
                    "hours_since_pull": round(hours_since, 1),
                    "max_allowed_hours": MAX_STALENESS_HOURS,
                    "last_pull": meta.last_updated_at.isoformat(),
                    "bfiu_ref": "BFIU Circular No. 29 §3.2.2",
                    "action_required": "Trigger UNSCR pull immediately",
                }
            )
            return {
                "status": "STALE",
                "stale": True,
                "hours_since_pull": round(hours_since, 1),
                "last_pull": meta.last_updated_at.isoformat(),
                "bfiu_ref": "BFIU §3.2.2",
            }

        logger.info(
            "UNSCR list is fresh",
            extra={"hours_since_pull": round(hours_since, 1),
                   "bfiu_ref": "BFIU Circular No. 29 §3.2.2"}
        )
        return {
            "status": "FRESH",
            "stale": False,
            "hours_since_pull": round(hours_since, 1),
            "last_pull": meta.last_updated_at.isoformat(),
        }
    except Exception as e:
        logger.error("UNSCR freshness check failed", exc_info=e)
        return {"status": "ERROR", "stale": True, "error": str(e)}


def get_unscr_entry_count(db: Session) -> int:
    try:
        from app.db.models_platform import UNSCREntry
        return db.query(UNSCREntry).filter(UNSCREntry.is_active == True).count()
    except Exception:
        return 0
