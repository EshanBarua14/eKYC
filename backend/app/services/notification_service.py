"""
Notification Service - M17
BFIU Circular No. 29 — Account opening notification requirement.
Sends SMS + Email on KYC success/failure.
Dev mode: logs to in-memory store (no real SMTP/SMS needed).
Prod mode: set SMTP_HOST + SMS_API_KEY env vars.
"""
import os
import uuid
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional

# ── config from env ────────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST",     "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM",     "noreply@xpertfintech.com")
SMS_API_KEY   = os.getenv("SMS_API_KEY",   "")
SMS_API_URL   = os.getenv("SMS_API_URL",   "https://api.smsprovider.bd/send")
DEV_MODE      = not bool(SMTP_HOST and SMTP_USER)

# ── in-memory delivery log ─────────────────────────────────────────────────
_notification_log: list = []

# ── templates ──────────────────────────────────────────────────────────────
TEMPLATES = {
    "KYC_SUCCESS_SMS": (
        "Dear {full_name}, your eKYC verification is complete. "
        "Account: {account_number}, Branch: {branch}, "
        "Type: {account_type}, Service No: {service_number}. "
        "Ref: {session_id}. - {institution_name}"
    ),
    "KYC_FAILURE_SMS": (
        "Dear Customer, your eKYC verification could not be completed. "
        "Reason: {reason}. Please contact helpdesk: {helpdesk_number}. "
        "Ref: {session_id}. - {institution_name}"
    ),
    "KYC_SUCCESS_EMAIL_SUBJECT": "eKYC Verification Successful — {institution_name}",
    "KYC_SUCCESS_EMAIL_BODY": """
Dear {full_name},

Your eKYC verification has been successfully completed.

Account Details:
  Account Name   : {full_name}
  Account Number : {account_number}
  Branch         : {branch}
  Account Type   : {account_type}
  Service Number : {service_number}
  KYC Type       : {kyc_type}
  Risk Grade     : {risk_grade}

Verification Details:
  Session ID     : {session_id}
  Timestamp      : {timestamp}
  Match Score    : {confidence}%
  BFIU Reference : BFIU Circular No. 29

This is an automated message. Please do not reply.
For queries, contact: {helpdesk_number}

{institution_name}
BFIU Circular No. 29 Compliant eKYC Platform
""",
    "KYC_FAILURE_EMAIL_SUBJECT": "eKYC Verification Failed — Action Required",
    "KYC_FAILURE_EMAIL_BODY": """
Dear Customer,

Your eKYC verification could not be completed.

Failure Details:
  Session ID     : {session_id}
  Step Failed    : {failed_step}
  Reason         : {reason}
  Timestamp      : {timestamp}

Please visit your nearest branch or contact our helpdesk:
  Helpdesk       : {helpdesk_number}
  Reference      : {session_id}

{institution_name}
""",
}


def _render(template_key: str, ctx: dict) -> str:
    try:
        return TEMPLATES[template_key].format(**ctx)
    except KeyError as e:
        return TEMPLATES[template_key]  # return unformatted if key missing


def _log_notification(
    notification_type: str,
    channel:           str,
    recipient:         str,
    session_id:        str,
    status:            str,
    message:           str,
    error:             str = "",
) -> dict:
    entry = {
        "id":                str(uuid.uuid4())[:8],
        "notification_type": notification_type,
        "channel":           channel,
        "recipient":         recipient,
        "session_id":        session_id,
        "status":            status,
        "message_preview":   message[:120],
        "error":             error,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "dev_mode":          DEV_MODE,
    }
    _notification_log.append(entry)
    return entry


def send_sms(mobile: str, message: str, session_id: str, notif_type: str) -> dict:
    """Send SMS. In dev mode, logs only. In prod, calls SMS gateway."""
    if DEV_MODE or not SMS_API_KEY:
        print(f"[DEV SMS] To: {mobile} | {message[:80]}...")
        return _log_notification(notif_type, "SMS", mobile, session_id, "DEV_LOGGED", message)

    try:
        import urllib.request, json as _json
        payload = _json.dumps({"to": mobile, "message": message, "api_key": SMS_API_KEY}).encode()
        req = urllib.request.Request(SMS_API_URL, data=payload,
                                     headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = "SENT" if resp.status == 200 else "FAILED"
    except Exception as e:
        return _log_notification(notif_type, "SMS", mobile, session_id, "FAILED", message, str(e))

    return _log_notification(notif_type, "SMS", mobile, session_id, status, message)


def send_email(to_email: str, subject: str, body: str, session_id: str, notif_type: str) -> dict:
    """Send email. In dev mode, logs only. In prod, uses SMTP."""
    if DEV_MODE or not SMTP_HOST:
        print(f"[DEV EMAIL] To: {to_email} | Subject: {subject}")
        return _log_notification(notif_type, "EMAIL", to_email, session_id, "DEV_LOGGED", body)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_FROM
        msg["To"]      = to_email
        msg.attach(MIMEText(body, "plain"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo(); server.starttls(context=ctx); server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return _log_notification(notif_type, "EMAIL", to_email, session_id, "SENT", body)
    except Exception as e:
        return _log_notification(notif_type, "EMAIL", to_email, session_id, "FAILED", body, str(e))


def notify_kyc_success(
    session_id:       str,
    full_name:        str,
    mobile:           str,
    email:            Optional[str],
    account_number:   str = "PENDING",
    branch:           str = "Head Office",
    account_type:     str = "Savings",
    service_number:   str = "N/A",
    kyc_type:         str = "SIMPLIFIED",
    risk_grade:       str = "LOW",
    confidence:       float = 0.0,
    institution_name: str = "Xpert Fintech Ltd.",
    helpdesk_number:  str = "16xxx",
    timestamp:        Optional[str] = None,
) -> dict:
    """Send KYC success notifications via SMS + Email."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    ctx = {
        "full_name": full_name, "session_id": session_id,
        "account_number": account_number, "branch": branch,
        "account_type": account_type, "service_number": service_number,
        "kyc_type": kyc_type, "risk_grade": risk_grade,
        "confidence": f"{confidence:.1f}", "timestamp": ts[:19].replace("T"," "),
        "institution_name": institution_name, "helpdesk_number": helpdesk_number,
    }
    results = {"session_id": session_id, "type": "KYC_SUCCESS", "channels": []}

    # SMS
    sms_msg = _render("KYC_SUCCESS_SMS", ctx)
    results["channels"].append(send_sms(mobile, sms_msg, session_id, "KYC_SUCCESS"))

    # Email
    if email:
        subj = _render("KYC_SUCCESS_EMAIL_SUBJECT", ctx)
        body = _render("KYC_SUCCESS_EMAIL_BODY", ctx)
        results["channels"].append(send_email(email, subj, body, session_id, "KYC_SUCCESS"))

    return results


def notify_kyc_failure(
    session_id:       str,
    mobile:           str,
    email:            Optional[str],
    failed_step:      str = "UNKNOWN",
    reason:           str = "Verification could not be completed",
    institution_name: str = "Xpert Fintech Ltd.",
    helpdesk_number:  str = "16xxx",
    timestamp:        Optional[str] = None,
) -> dict:
    """Send KYC failure notifications via SMS + Email."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    ctx = {
        "session_id": session_id, "failed_step": failed_step,
        "reason": reason, "timestamp": ts[:19].replace("T"," "),
        "institution_name": institution_name, "helpdesk_number": helpdesk_number,
    }
    results = {"session_id": session_id, "type": "KYC_FAILURE", "channels": []}

    sms_msg = _render("KYC_FAILURE_SMS", ctx)
    results["channels"].append(send_sms(mobile, sms_msg, session_id, "KYC_FAILURE"))

    if email:
        subj = _render("KYC_FAILURE_EMAIL_SUBJECT", ctx)
        body = _render("KYC_FAILURE_EMAIL_BODY", ctx)
        results["channels"].append(send_email(email, subj, body, session_id, "KYC_FAILURE"))

    return results


def get_notification_log(session_id: Optional[str] = None, limit: int = 100) -> list:
    logs = list(_notification_log)
    if session_id:
        logs = [l for l in logs if l["session_id"] == session_id]
    return logs[-limit:]


def get_delivery_stats() -> dict:
    total  = len(_notification_log)
    sent   = len([l for l in _notification_log if l["status"] in ("SENT","DEV_LOGGED")])
    failed = len([l for l in _notification_log if l["status"] == "FAILED"])
    sms    = len([l for l in _notification_log if l["channel"] == "SMS"])
    email  = len([l for l in _notification_log if l["channel"] == "EMAIL"])
    return {
        "total": total, "sent": sent, "failed": failed,
        "sms_count": sms, "email_count": email,
        "dev_mode": DEV_MODE,
        "smtp_configured": bool(SMTP_HOST),
        "sms_configured":  bool(SMS_API_KEY),
    }
