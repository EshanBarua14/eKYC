"""
Notification Service - M17 + M26
BFIU Circular No. 29 — reads config from platform_settings.json (UI-configurable)
"""
import os, json, uuid, smtplib, ssl, requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models import NotificationLog

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "../../platform_settings.json")

def _load_cfg():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _now(): return datetime.now(timezone.utc)

TEMPLATES = {
    "KYC_SUCCESS_SMS": (
        "Dear {full_name}, your eKYC verification is complete. "
        "Account: {account_number}, Branch: {branch}, Type: {account_type}. "
        "Ref: {session_id}. - {institution_name}"
    ),
    "KYC_FAILURE_SMS": (
        "Dear Customer, your eKYC verification could not be completed. "
        "Reason: {reason}. Helpdesk: {helpdesk_number}. Ref: {session_id}."
    ),
}

def _log(notification_type:str, channel:str, recipient:str, session_id:str,
         status:str, message_preview:str="", error:str="", dev_mode:bool=True):
    entry = NotificationLog(
        id=str(uuid.uuid4())[:8], notification_type=notification_type,
        channel=channel, recipient=recipient, session_id=session_id,
        status=status, message_preview=message_preview[:200],
        error=error[:500] if error else None, dev_mode=dev_mode,
        timestamp=_now(),
    )
    try:
        with db_session() as db:
            db.add(entry)
    except Exception as e:
        print(f"[NOTIF LOG ERROR] {e}")

def _send_sms(mobile:str, message:str, session_id:str) -> dict:
    cfg = _load_cfg()
    api_key = cfg.get("sms_api_key","") or os.getenv("SMS_API_KEY","")
    api_url = cfg.get("sms_api_url","") or os.getenv("SMS_API_URL","")
    if not api_key:
        print(f"[DEV SMS] To: {mobile} | {message[:80]}...")
        _log("SMS","SMS",mobile,session_id,"DEV_LOGGED",message[:80],dev_mode=True)
        return {"status":"DEV_LOGGED","mobile":mobile}
    try:
        r = requests.post(api_url, json={"api_key":api_key,"to":mobile,"message":message}, timeout=10)
        status = "SENT" if r.status_code==200 else "FAILED"
        _log("SMS","SMS",mobile,session_id,status,message[:80],dev_mode=False)
        return {"status":status,"response":r.text[:100]}
    except Exception as e:
        _log("SMS","SMS",mobile,session_id,"FAILED","",str(e),dev_mode=False)
        return {"status":"FAILED","error":str(e)}

def _send_email(to:str, subject:str, body:str, session_id:str) -> dict:
    cfg = _load_cfg()
    host = cfg.get("smtp_host","") or os.getenv("SMTP_HOST","")
    user = cfg.get("smtp_user","") or os.getenv("SMTP_USER","")
    pwd  = cfg.get("smtp_password","") or os.getenv("SMTP_PASSWORD","")
    frm  = cfg.get("smtp_from","noreply@xpertfintech.com.bd")
    if not host or not user:
        print(f"[DEV EMAIL] To: {to} | {subject}")
        _log("EMAIL","EMAIL",to,session_id,"DEV_LOGGED",subject,dev_mode=True)
        return {"status":"DEV_LOGGED","to":to}
    try:
        msg = MIMEMultipart(); msg["From"]=frm; msg["To"]=to; msg["Subject"]=subject
        msg.attach(MIMEText(body,"plain"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, int(cfg.get("smtp_port",587))) as s:
            s.starttls(context=ctx); s.login(user,pwd); s.send_message(msg)
        _log("EMAIL","EMAIL",to,session_id,"SENT",subject,dev_mode=False)
        return {"status":"SENT","to":to}
    except Exception as e:
        _log("EMAIL","EMAIL",to,session_id,"FAILED",subject,str(e),dev_mode=False)
        return {"status":"FAILED","error":str(e)}

def notify_kyc_success(session_id:str, full_name:str, mobile:str,
    email:Optional[str]=None, account_number:str="PENDING",
    branch:str="Head Office", account_type:str="eKYC Account",
    service_number:str="", kyc_type:str="SIMPLIFIED",
    risk_grade:str="LOW", confidence:float=0.0,
    institution_name:str=None, **kwargs) -> dict:
    cfg = _load_cfg()
    inst = cfg.get("institution_name","Xpert Fintech Ltd.")
    sms_msg = TEMPLATES["KYC_SUCCESS_SMS"].format(
        full_name=full_name, account_number=account_number,
        branch=branch, account_type=account_type,
        service_number=service_number or session_id,
        session_id=session_id, institution_name=inst)
    results = {"sms": _send_sms(mobile, sms_msg, session_id)}
    if email:
        results["email"] = _send_email(email,
            f"eKYC Verification Successful — {inst}",
            f"Dear {full_name},\nYour eKYC is complete.\nSession: {session_id}\nRisk: {risk_grade}",
            session_id)
    return {"status":"sent","session_id":session_id,"channels":results}

def notify_kyc_failure(session_id:str, mobile:str, reason:str="Verification failed",
    email:Optional[str]=None, failed_step:str=None, **kwargs) -> dict:
    cfg = _load_cfg()
    helpdesk = cfg.get("helpdesk_number","+880-2-XXXXXXXX")
    inst = cfg.get("institution_name","Xpert Fintech Ltd.")
    sms_msg = TEMPLATES["KYC_FAILURE_SMS"].format(
        reason=reason, helpdesk_number=helpdesk, session_id=session_id)
    results = {"sms": _send_sms(mobile, sms_msg, session_id)}
    return {"status":"sent","session_id":session_id,"channels":results}

def get_log(session_id:Optional[str]=None, limit:int=50) -> list:
    with db_session() as db:
        q = db.query(NotificationLog)
        if session_id: q=q.filter(NotificationLog.session_id==session_id)
        rows = q.order_by(NotificationLog.timestamp.desc()).limit(limit).all()
        return [{"id":r.id,"type":r.notification_type,"channel":r.channel,
                 "recipient":r.recipient,"session_id":r.session_id,
                 "status":r.status,"timestamp":str(r.timestamp),
                 "dev_mode":r.dev_mode} for r in rows]

def get_stats() -> dict:
    with db_session() as db:
        total = db.query(NotificationLog).count()
        sent  = db.query(NotificationLog).filter_by(status="SENT").count()
        dev   = db.query(NotificationLog).filter_by(status="DEV_LOGGED").count()
        sms=db.query(NotificationLog).filter_by(channel="SMS").count()
        email=db.query(NotificationLog).filter_by(channel="EMAIL").count()
        return {"total":total,"sent":sent,"dev_logged":dev,"failed":total-sent-dev,"sms_count":sms,"email_count":email,"dev_mode":dev>0}

# ── Backward-compatible aliases ────────────────────────────────────────────
get_notification_log = get_log
get_notification_stats = get_stats
list_notifications = get_log

get_delivery_stats = get_stats



# ── Backward-compatible aliases ────────────────────────────
DEV_MODE = False  # runtime config from settings
