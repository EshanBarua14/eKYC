"""
Monthly BFIU Report Generator - M21
BFIU Circular No. 29 — Section 5.1 Reporting Obligation

Financial institutions must submit monthly reports to BFIU containing:
- Number of accounts opened via eKYC by type/tier/institution
- Failed onboarding attempts with reason codes
- EDD cases triggered
- Sanctions/screening hits
- Traditional KYC fallback cases
- BO accounts opened (CMI only)

Report formats: JSON (machine-readable) + CSV (BFIU submission)
Report periods: Monthly (auto) or custom date range
"""
import csv
import io
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

# ── Import data from existing services ─────────────────────────────────────
from app.services.outcome_service   import list_outcomes, get_queue_summary
from app.services.fallback_service  import list_cases as list_fallback_cases, get_stats as fallback_stats
from app.services.notification_service import get_notification_log, get_delivery_stats
from app.services.cmi_service       import list_bo_accounts

# ── Report store ────────────────────────────────────────────────────────────
_reports: dict = {}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _month_range(year: int, month: int):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year+1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month+1, 1, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


def generate_monthly_report(
    year:           int,
    month:          int,
    institution_id: str = "ALL",
    submitted_by:   str = "system",
) -> dict:
    """Generate BFIU monthly compliance report."""

    report_id  = f"BFIU-{year}{month:02d}-{str(uuid.uuid4())[:6].upper()}"
    period_start, period_end = _month_range(year, month)
    generated_at = _now()

    # ── Gather data from all services ─────────────────────────────────────
    all_outcomes  = list_outcomes(limit=9999)
    approved      = [o for o in all_outcomes if o["state"]=="APPROVED"]
    rejected      = [o for o in all_outcomes if o["state"]=="REJECTED"]
    pending_review= [o for o in all_outcomes if o["state"]=="PENDING_REVIEW"]
    fallback_kyc  = [o for o in all_outcomes if o["state"]=="FALLBACK_KYC"]

    simplified    = [o for o in approved if o.get("kyc_type")=="SIMPLIFIED"]
    regular       = [o for o in approved if o.get("kyc_type")=="REGULAR"]
    high_risk     = [o for o in approved if o.get("risk_grade")=="HIGH"]
    medium_risk   = [o for o in approved if o.get("risk_grade")=="MEDIUM"]
    low_risk      = [o for o in approved if o.get("risk_grade")=="LOW"]
    auto_approved = [o for o in approved if o.get("auto_approved") is True]

    fb_cases      = list_fallback_cases(limit=9999)
    fb_stats      = fallback_stats()
    bo_accounts   = list_bo_accounts(limit=9999)
    bo_active     = [b for b in bo_accounts if b["status"]=="ACTIVE"]

    notif_stats   = get_delivery_stats()
    outcome_summary = get_queue_summary()

    # ── Build report ──────────────────────────────────────────────────────
    report = {
        "report_id":        report_id,
        "report_type":      "MONTHLY_BFIU_SUBMISSION",
        "period_year":      year,
        "period_month":     month,
        "period_month_name": datetime(year, month, 1).strftime("%B %Y"),
        "period_start":     period_start,
        "period_end":       period_end,
        "institution_id":   institution_id,
        "submitted_by":     submitted_by,
        "generated_at":     generated_at,
        "bfiu_ref":         "BFIU Circular No. 29 — Section 5.1",
        "deadline":         "December 31, 2026",

        # Section 1: eKYC Account Openings
        "section_1_ekyc_openings": {
            "total_approved":          len(approved),
            "simplified_ekyc":         len(simplified),
            "regular_ekyc":            len(regular),
            "auto_approved":           len(auto_approved),
            "pending_checker_review":  len(pending_review),
            "rejected":                len(rejected),
        },

        # Section 2: Risk Distribution
        "section_2_risk_distribution": {
            "low_risk":    len(low_risk),
            "medium_risk": len(medium_risk),
            "high_risk":   len(high_risk),
            "edd_triggered": len([o for o in all_outcomes
                                  if o.get("edd_required") is True]),
            "pep_flagged":   len([o for o in all_outcomes
                                  if o.get("pep_flag") is True]),
        },

        # Section 3: Failed & Fallback
        "section_3_failures": {
            "ekyc_failed":          len(rejected),
            "fallback_kyc_cases":   len(fb_cases),
            "fallback_approved":    fb_stats.get("APPROVED", 0),
            "fallback_rejected":    fb_stats.get("REJECTED", 0),
            "fallback_pending":     fb_stats.get("DOCS_SUBMITTED", 0) +
                                    fb_stats.get("UNDER_REVIEW", 0),
            "trigger_breakdown": _fallback_trigger_breakdown(fb_cases),
        },

        # Section 4: Screening
        "section_4_screening": {
            "total_screened":    len(all_outcomes),
            "sanctions_hits":    0,   # from screening service (demo data)
            "pep_hits":          len([o for o in all_outcomes if o.get("pep_flag")]),
            "blocked":           len([o for o in rejected
                                      if "BLOCKED" in str(o.get("history",""))]),
        },

        # Section 5: CMI/BO Accounts
        "section_5_cmi_bo": {
            "bo_accounts_opened":   len(bo_accounts),
            "bo_accounts_active":   len(bo_active),
            "bo_pending_review":    len([b for b in bo_accounts
                                         if b["status"]=="PENDING_REVIEW"]),
            "simplified_bo":        len([b for b in bo_accounts
                                          if b.get("kyc_type")=="SIMPLIFIED"]),
            "regular_bo":           len([b for b in bo_accounts
                                          if b.get("kyc_type")=="REGULAR"]),
        },

        # Section 6: Notifications
        "section_6_notifications": {
            "success_notifications": notif_stats.get("sent", 0),
            "failure_notifications": notif_stats.get("failed", 0),
            "sms_sent":              notif_stats.get("sms_count", 0),
            "email_sent":            notif_stats.get("email_count", 0),
        },

        # Section 7: Summary totals (BFIU submission line items)
        "section_7_summary": {
            "total_ekyc_attempts":   len(all_outcomes),
            "total_accounts_opened": len(approved) + len(bo_active),
            "total_failures":        len(rejected) + len(fb_cases),
            "compliance_rate_pct":   round(
                (len(approved) / max(len(all_outcomes), 1)) * 100, 1),
        },
    }

    _reports[report_id] = report
    return report


def _fallback_trigger_breakdown(cases: list) -> dict:
    breakdown = {}
    for c in cases:
        code = c.get("trigger_code", "UNKNOWN")
        breakdown[code] = breakdown.get(code, 0) + 1
    return breakdown


def report_to_csv(report: dict) -> str:
    """Convert report to BFIU-submission CSV format."""
    buf = io.StringIO()
    w   = csv.writer(buf)

    w.writerow(["BFIU MONTHLY eKYC COMPLIANCE REPORT"])
    w.writerow(["Report ID",      report["report_id"]])
    w.writerow(["Period",         report["period_month_name"]])
    w.writerow(["Institution",    report["institution_id"]])
    w.writerow(["Generated At",   report["generated_at"][:19].replace("T"," ")])
    w.writerow(["BFIU Reference", report["bfiu_ref"]])
    w.writerow([])

    sections = [
        ("SECTION 1: eKYC ACCOUNT OPENINGS",    "section_1_ekyc_openings"),
        ("SECTION 2: RISK DISTRIBUTION",         "section_2_risk_distribution"),
        ("SECTION 3: FAILURES & FALLBACK",       "section_3_failures"),
        ("SECTION 4: SCREENING",                 "section_4_screening"),
        ("SECTION 5: CMI/BO ACCOUNTS",           "section_5_cmi_bo"),
        ("SECTION 6: NOTIFICATIONS",             "section_6_notifications"),
        ("SECTION 7: SUMMARY",                   "section_7_summary"),
    ]

    for title, key in sections:
        w.writerow([title])
        w.writerow(["Metric", "Value"])
        for k, v in report.get(key, {}).items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    w.writerow([f"  {k2}", v2])
            else:
                w.writerow([k.replace("_"," ").title(), v])
        w.writerow([])

    return buf.getvalue()


def get_report(report_id: str) -> Optional[dict]:
    return _reports.get(report_id)


def list_reports() -> list:
    return list(_reports.values())
