"""
M77: Account opening notification dispatch — BFIU Circular No. 29 §3.2 Step 5
Celery task — fires SMS + email asynchronously after KYC profile approved/created.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from app.worker.celery_app import celery_app
from app.services.notification_service import notify_kyc_success, notify_kyc_failure

log = logging.getLogger(__name__)
BST = timezone(timedelta(hours=6))


def _bst_now() -> str:
    return datetime.now(BST).strftime("%Y-%m-%d %H:%M:%S BST")


@celery_app.task(
    name="notify.account_opening_success",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_account_opening_success(
    self,
    session_id: str,
    full_name: str,
    mobile: str,
    email: str | None = None,
    account_number: str = "PENDING",
    branch: str = "Head Office",
    account_type: str = "eKYC Account",
    kyc_type: str = "SIMPLIFIED",
    risk_grade: str = "LOW",
    confidence: float = 0.0,
    institution_name: str = "Xpert Fintech Ltd.",
) -> dict:
    """
    BFIU §3.2 Step 5 — notify customer of successful account opening.
    Retries up to 3 times on transient failure.
    """
    log.info("[M77] Account opening success notify — session=%s mobile=%s BST=%s",
             session_id, mobile, _bst_now())
    try:
        result = notify_kyc_success(
            session_id=session_id,
            full_name=full_name,
            mobile=mobile,
            email=email,
            account_number=account_number,
            branch=branch,
            account_type=account_type,
            kyc_type=kyc_type,
            risk_grade=risk_grade,
            confidence=confidence,
            institution_name=institution_name,
        )
        log.info("[M77] Notify success dispatched: %s", result)
        return result
    except Exception as exc:
        log.error("[M77] Notify failed (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="notify.account_opening_failure",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_account_opening_failure(
    self,
    session_id: str,
    mobile: str,
    reason: str = "Verification failed",
    email: str | None = None,
    failed_step: str | None = None,
) -> dict:
    """
    BFIU §3.2 — notify customer of failed verification.
    """
    log.info("[M77] Account opening failure notify — session=%s BST=%s",
             session_id, _bst_now())
    try:
        result = notify_kyc_failure(
            session_id=session_id,
            mobile=mobile,
            reason=reason,
            email=email,
            failed_step=failed_step,
        )
        log.info("[M77] Failure notify dispatched: %s", result)
        return result
    except Exception as exc:
        log.error("[M77] Failure notify failed: %s", exc)
        raise self.retry(exc=exc)
