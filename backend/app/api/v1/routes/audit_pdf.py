"""
Audit Export PDF Routes - M31
GET  /audit/export/pdf              - Export full audit log as PDF
GET  /audit/export/pdf/session/{id} - Export session audit as PDF
POST /audit/export/pdf/custom       - Export with filters as PDF
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.services.audit_service import list_entries
from app.services.audit_pdf_service import generate_audit_pdf, generate_session_audit_pdf
from app.middleware.rbac import require_admin_or_auditor

router = APIRouter(prefix="/audit", tags=["Audit Export PDF"])


class AuditPDFRequest(BaseModel):
    institution_id: Optional[str] = None
    event_type:     Optional[str] = None
    actor_id:       Optional[str] = None
    date_from:      Optional[str] = None
    date_to:        Optional[str] = None
    limit:          int = 500
    report_title:   str = "Audit Trail Report"
    generated_by:   str = "compliance_officer"


@router.get("/export/pdf", operation_id="audit_export_pdf")
async def export_audit_pdf(
    institution_id: Optional[str] = None,
    limit: int = Query(500, le=2000),
    cu: dict = Depends(require_admin_or_auditor),
):
    """Export audit log as BFIU-compliant PDF. Requires ADMIN or AUDITOR role."""
    entries = list_entries(institution_id=institution_id, limit=limit)
    pdf_bytes = generate_audit_pdf(
        entries=entries,
        institution_id=institution_id,
        generated_by=cu.get("sub", "system"),
        report_title="Audit Trail Report",
    )
    filename = f"audit_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/pdf/session/{session_id}", operation_id="audit_export_session_pdf")
async def export_session_audit_pdf(
    session_id: str,
    cu: dict = Depends(require_admin_or_auditor),
):
    """Export audit log for a specific session as PDF."""
    entries = list_entries(session_id=session_id, limit=200)
    if not entries:
        raise HTTPException(404, f"No audit entries for session {session_id!r}")
    pdf_bytes = generate_session_audit_pdf(session_id=session_id, entries=entries)
    filename = f"session_audit_{session_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/pdf/custom", status_code=201, operation_id="audit_export_pdf_custom")
async def export_audit_pdf_custom(
    req: AuditPDFRequest,
    cu: dict = Depends(require_admin_or_auditor),
):
    """Export filtered audit log as PDF with custom parameters."""
    entries = list_entries(
        institution_id=req.institution_id,
        event_type=req.event_type,
        actor_id=req.actor_id,
        limit=req.limit,
    )
    pdf_bytes = generate_audit_pdf(
        entries=entries,
        institution_id=req.institution_id,
        generated_by=req.generated_by,
        report_title=req.report_title,
        date_from=req.date_from,
        date_to=req.date_to,
    )
    import base64
    return {
        "pdf_b64":       base64.b64encode(pdf_bytes).decode(),
        "size_bytes":    len(pdf_bytes),
        "entry_count":   len(entries),
        "report_title":  req.report_title,
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "bfiu_ref":      "BFIU Circular No. 29 - Section 5.1",
    }
