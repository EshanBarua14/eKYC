"""
Notification Routes - M17
BFIU Circular No. 29 — Mandatory account opening notifications.

POST /notify/kyc-success   - Send success notification (SMS + Email)
POST /notify/kyc-failure   - Send failure notification (SMS + Email)
GET  /notify/log           - Delivery log for audit
GET  /notify/stats         - Delivery statistics
GET  /notify/templates     - View notification templates
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.notification_service import (
    notify_kyc_success, notify_kyc_failure,
    get_notification_log, get_delivery_stats, TEMPLATES, DEV_MODE,
)

router = APIRouter(prefix="/notify", tags=["Notifications"])


class SuccessNotifyRequest(BaseModel):
    session_id:       str
    full_name:        str
    mobile:           str
    email:            Optional[str]  = None
    account_number:   str            = "PENDING"
    branch:           str            = "Head Office"
    account_type:     str            = "Savings"
    service_number:   str            = "N/A"
    kyc_type:         str            = "SIMPLIFIED"
    risk_grade:       str            = "LOW"
    confidence:       float          = 0.0
    institution_name: str            = "Xpert Fintech Ltd."
    helpdesk_number:  str            = "16xxx"
    timestamp:        Optional[str]  = None


class FailureNotifyRequest(BaseModel):
    session_id:       str
    mobile:           str
    email:            Optional[str]  = None
    failed_step:      str            = "UNKNOWN"
    reason:           str            = "Verification could not be completed"
    institution_name: str            = "Xpert Fintech Ltd."
    helpdesk_number:  str            = "16xxx"
    timestamp:        Optional[str]  = None


@router.post("/kyc-success", status_code=201)
def notify_kyc_success(req: SuccessNotifyRequest):
    """
    Send KYC success notification via SMS + Email.
    BFIU mandates: account name, number, branch, type, service number.
    """
    result = notify_kyc_success(
        session_id       = req.session_id,
        full_name        = req.full_name,
        mobile           = req.mobile,
        email            = req.email,
        account_number   = req.account_number,
        branch           = req.branch,
        account_type     = req.account_type,
        service_number   = req.service_number,
        kyc_type         = req.kyc_type,
        risk_grade       = req.risk_grade,
        confidence       = req.confidence,
        institution_name = req.institution_name,
        helpdesk_number  = req.helpdesk_number,
        timestamp        = req.timestamp,
    )
    return {
        **result,
        "bfiu_ref":   "BFIU Circular No. 29 — Account Opening Notification",
        "dev_mode":   DEV_MODE,
        "channels_notified": len(result["channels"]),
    }


@router.post("/kyc-failure", status_code=201)
def notify_kyc_failure(req: FailureNotifyRequest):
    """
    Send KYC failure notification via SMS + Email.
    BFIU mandates failure notification with helpdesk contact.
    """
    result = notify_kyc_failure(
        session_id       = req.session_id,
        mobile           = req.mobile,
        email            = req.email,
        failed_step      = req.failed_step,
        reason           = req.reason,
        institution_name = req.institution_name,
        helpdesk_number  = req.helpdesk_number,
        timestamp        = req.timestamp,
    )
    return {
        **result,
        "bfiu_ref": "BFIU Circular No. 29 — Failure Notification",
        "dev_mode": DEV_MODE,
        "channels_notified": len(result["channels"]),
    }


@router.get("/log")
def notify_log(
    session_id: Optional[str] = None,
    limit:      int = Query(100, le=500),
):
    """Delivery log for audit — retained 5 years per BFIU §5.1."""
    logs = get_notification_log(session_id, limit)
    return {
        "logs":  logs,
        "total": len(logs),
        "bfiu_ref": "BFIU Circular No. 29 — Section 5.1 Retention",
    }


@router.get("/stats")
def notify_stats():
    """Delivery statistics and provider configuration status."""
    return get_delivery_stats()


@router.get("/templates")
def notify_templates():
    """View all notification templates."""
    return {
        "templates": {k: v[:120]+"..." if len(v)>120 else v for k,v in TEMPLATES.items()},
        "total": len(TEMPLATES),
        "bfiu_required": ["KYC_SUCCESS_SMS","KYC_FAILURE_SMS"],
    }
