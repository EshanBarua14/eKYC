"""BFIU Monthly Report Service - M21 + M26 PostgreSQL backed"""
import uuid, calendar
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models import BFIUReport, KYCProfile, OnboardingOutcome, FallbackCase, ConsentRecord

def _now(): return datetime.now(timezone.utc)

def _row(r):
    return {"report_id":r.report_id,"report_type":r.report_type,
            "period_year":r.period_year,"period_month":r.period_month,
            "institution_id":r.institution_id,"submitted_by":r.submitted_by,
            "report_data":r.report_data,"generated_at":str(r.generated_at)}

def generate_monthly_report(year, month, institution_id="default", submitted_by="system"):
    with db_session() as db:
        profiles  = db.query(KYCProfile).all()
        outcomes  = db.query(OnboardingOutcome).all()
        fallbacks = db.query(FallbackCase).all()
        consents  = db.query(ConsentRecord).all()
        simplified  = len([p for p in profiles if p.kyc_type=="SIMPLIFIED"])
        regular     = len([p for p in profiles if p.kyc_type=="REGULAR"])
        approved    = len([o for o in outcomes if o.state=="APPROVED"])
        rejected    = len([o for o in outcomes if o.state=="REJECTED"])
        pending     = len([o for o in outcomes if o.state=="PENDING_REVIEW"])
        auto_appr   = len([o for o in outcomes if o.auto_approved])
        fb_count    = len(fallbacks)
        total       = len(outcomes) if outcomes else len(profiles)
        pep_flagged = len([p for p in profiles if getattr(p,"pep_flag",False)])
        edd_cases   = len([p for p in profiles if getattr(p,"edd_required",False)])
        compliance  = round(min((approved/max(total,1))*100, 100.0), 2)
        period_name = f"{calendar.month_name[month]} {year}"
        report_data = {
            "period":f"{year}-{month:02d}","period_year":year,"period_month":month,
            "period_month_name":period_name,"institution_id":institution_id,
            "generated_at":_now().isoformat(),
            "section_1_ekyc_openings":{
                "total":total,"total_approved":approved,"simplified_ekyc":simplified,
                "regular_ekyc":regular,"auto_approved":auto_appr,
                "pending_checker_review":pending,"rejected":rejected,
                "period":f"{year}-{month:02d}","period_year":year,
                "period_month":month,"period_month_name":period_name},
            "section_2_risk_distribution":{
                "low_risk":   len([p for p in profiles if getattr(p,"risk_grade","LOW")=="LOW"]),
                "medium_risk":len([p for p in profiles if getattr(p,"risk_grade","")=="MEDIUM"]),
                "high_risk":  len([p for p in profiles if getattr(p,"risk_grade","")=="HIGH"]),
                "edd_cases":edd_cases,"edd_triggered":edd_cases,"pep_flagged":pep_flagged},
            "section_3_failures":{
                "total_failed":rejected,"ekyc_failed":rejected,
                "fallback_cases":fb_count,"fallback_kyc_cases":fb_count,
                "fallback_approved":0,"fallback_rejected":0,
                "trigger_breakdown":[],"failure_reasons":[]},
            "section_4_screening":{
                "total_screened":total,"unscr_checks":len(consents),
                "pep_hits":pep_flagged,"blocked":rejected,"clear":approved},
            "section_5_cmi_bo":{
                "bo_accounts_opened":0,"bo_accounts_active":0,
                "simplified_bo":0,"regular_bo":0,"threshold_bdt":1500000},
            "section_6_notifications":{
                "total_sent":len(consents),"sms_sent":len(consents),"email_sent":0,"failed":0},
            "section_7_summary":{
                "pep_flagged":pep_flagged,"total_ekyc_attempts":total,
                "total_onboardings":total,"total_accounts_opened":approved,
                "approved":approved,"rejected":rejected,"pending":pending,
                "total_failures":rejected+fb_count,"compliance_rate":compliance,
                "compliance_rate_pct":compliance,
                "bfiu_ref":"BFIU Circular No. 29","deadline":"December 31, 2026"},
        }
        report_id = f"BFIU-{year}-{month:02d}-{str(uuid.uuid4())[:6].upper()}"
        r=BFIUReport(report_id=report_id,report_type="MONTHLY_ACTIVITY",
            period_year=year,period_month=month,institution_id=institution_id,
            submitted_by=submitted_by,report_data=report_data,generated_at=_now())
        db.add(r); db.flush()
        return {"report_id":report_id, **report_data}

def list_reports(institution_id=None, limit=24):
    with db_session() as db:
        q = db.query(BFIUReport)
        if institution_id: q = q.filter_by(institution_id=institution_id)
        return [_row(r) for r in q.order_by(BFIUReport.generated_at.desc()).limit(limit).all()]

def get_report(report_id):
    with db_session() as db:
        r = db.query(BFIUReport).filter_by(report_id=report_id).first()
        return _row(r) if r else None

def report_to_csv(report_id=None):
    import csv, io
    reports = list_reports(limit=1000)
    buf = io.StringIO()
    buf.write("BFIU Circular No. 29 Monthly Activity Report\n")
    buf.write("SECTION 1: eKYC Openings\n")
    buf.write(f"Generated: {_now().isoformat()}\n\n")
    if reports:
        w = csv.DictWriter(buf, fieldnames=["report_id","period_year","period_month","institution_id","generated_at"])
        w.writeheader()
        for r in reports:
            w.writerow({k:r.get(k,"") for k in ["report_id","period_year","period_month","institution_id","generated_at"]})
    return buf.getvalue()
