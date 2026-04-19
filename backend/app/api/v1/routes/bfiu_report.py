"""
Monthly BFIU Report Routes - M21
BFIU Circular No. 29 — Section 5.1

POST /bfiu-report/generate         - Generate monthly report
GET  /bfiu-report/{report_id}      - Get report by ID
GET  /bfiu-report/{report_id}/csv  - Download as CSV
GET  /bfiu-report/list/all         - List all generated reports
GET  /bfiu-report/current-month    - Generate for current month instantly
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.services.bfiu_report_service import (
    generate_monthly_report, report_to_csv,
    get_report, list_reports,
)

router = APIRouter(prefix="/bfiu-report", tags=["BFIU Monthly Report"])


class GenerateReportRequest(BaseModel):
    year:           int
    month:          int   # 1-12
    institution_id: str   = "ALL"
    submitted_by:   str   = "compliance_officer"


@router.post("/generate", status_code=201, operation_id="bfiu_generate")
async def generate(req: GenerateReportRequest):
    """Generate BFIU monthly compliance report."""
    if not (1 <= req.month <= 12):
        raise HTTPException(400, "month must be between 1 and 12")
    if req.year < 2024 or req.year > 2030:
        raise HTTPException(400, "year must be between 2024 and 2030")
    report = generate_monthly_report(
        req.year, req.month, req.institution_id, req.submitted_by)
    return {
        "report":   report,
        "bfiu_ref": "BFIU Circular No. 29 — Section 5.1",
    }


@router.get("/current-month",     operation_id="bfiu_current_month")
async def current_month_report():
    """Generate report for the current month instantly."""
    now   = datetime.now(timezone.utc)
    report = generate_monthly_report(now.year, now.month)
    return {"report": report}


@router.get("/list/all",          operation_id="bfiu_list_all")
async def list_all_reports():
    """List all generated BFIU reports."""
    reports = list_reports()
    return {"reports": reports, "total": len(reports)}


@router.get("/{report_id}/csv",   operation_id="bfiu_download_csv")
async def download_csv(report_id: str):
    """Download report as BFIU-submission CSV."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(404, f"Report '{report_id}' not found")
    csv_data = report_to_csv(report)
    filename = f"bfiu_report_{report['period_year']}_{report['period_month']:02d}.csv"
    return Response(
        content    = csv_data,
        media_type = "text/csv",
        headers    = {"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{report_id}",       operation_id="bfiu_get_report")
async def get_report_by_id(report_id: str):
    """Get BFIU report by ID."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(404, f"Report '{report_id}' not found")
    return {"report": report}
