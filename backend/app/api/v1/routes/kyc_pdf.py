"""
KYC PDF Route - M15
GET  /api/v1/kyc/profile/{session_id}/pdf  — download PDF
POST /api/v1/kyc/pdf/generate              — generate from raw verification data
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.services.pdf_service import generate_kyc_pdf

router = APIRouter(prefix="/kyc", tags=["KYC PDF"])

# ── in-memory PDF store (keyed by session_id) ──────────────────────────────
_pdf_store: dict = {}

class PDFRequest(BaseModel):
    session_id:       str
    verdict:          str
    confidence:       float
    timestamp:        Optional[str]  = None
    processing_ms:    int            = 0
    bfiu_ref:         str            = "BFIU Circular No. 29"
    full_name:        str            = "N/A"
    date_of_birth:    str            = "N/A"
    mobile:           str            = "N/A"
    fathers_name:     Optional[str]  = None
    mothers_name:     Optional[str]  = None
    spouse_name:      Optional[str]  = None
    gender:           Optional[str]  = None
    nationality:      str            = "Bangladeshi"
    profession:       Optional[str]  = None
    present_address:  Optional[str]  = None
    permanent_address:Optional[str]  = None
    kyc_type:         str            = "SIMPLIFIED"
    institution_type: str            = "INSURANCE"
    product_type:     Optional[str]  = None
    risk_grade:       str            = "LOW"
    risk_score:       int            = 0
    edd_required:     bool           = False
    status:           str            = "PENDING"
    pep_flag:         bool           = False
    unscr_checked:    bool           = False
    screening_result: str            = "CLEAR"
    liveness_passed:  bool           = True
    liveness_score:   int            = 0
    liveness_max:     int            = 5
    ssim_score:       float          = 0
    orb_score:        float          = 0
    histogram_score:  float          = 0
    pixel_score:      float          = 0
    agent_id:         str            = "N/A"
    institution_id:   str            = "N/A"
    geolocation:      str            = "N/A"


@router.post("/pdf/generate", status_code=201)
async def generate_pdf(req: PDFRequest):
    """Generate KYC PDF from verification data and cache it."""
    if req.verdict not in ("MATCHED", "REVIEW", "FAILED"):
        raise HTTPException(400, "verdict must be MATCHED, REVIEW, or FAILED")

    data = req.model_dump()
    if not data.get("timestamp"):
        data["timestamp"] = datetime.now(timezone.utc).isoformat()

    pdf_bytes = generate_kyc_pdf(**data)
    _pdf_store[req.session_id] = {
        "pdf":        pdf_bytes,
        "session_id": req.session_id,
        "verdict":    req.verdict,
        "full_name":  req.full_name,
        "generated_at": data["timestamp"],
        "size_bytes": len(pdf_bytes),
    }
    return {
        "session_id":   req.session_id,
        "generated_at": data["timestamp"],
        "size_bytes":   len(pdf_bytes),
        "download_url": f"/api/v1/kyc/profile/{req.session_id}/pdf",
        "bfiu_ref":     req.bfiu_ref,
    }


@router.get("/profile/{session_id}/pdf")
async def download_pdf(session_id: str):
    """Download the generated KYC PDF for a session."""
    if session_id not in _pdf_store:
        raise HTTPException(404, f"No PDF found for session '{session_id}'. Call POST /pdf/generate first.")
    pdf_bytes = _pdf_store[session_id]["pdf"]
    filename  = f"kyc_certificate_{session_id}.pdf"
    return Response(
        content     = pdf_bytes,
        media_type  = "application/pdf",
        headers     = {"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/pdf/list")
async def list_pdfs():
    """List all generated PDFs (admin)."""
    return {
        "pdfs":  [{"session_id":v["session_id"],"verdict":v["verdict"],
                   "full_name":v["full_name"],"generated_at":v["generated_at"],
                   "size_bytes":v["size_bytes"]}
                  for v in _pdf_store.values()],
        "total": len(_pdf_store),
    }
