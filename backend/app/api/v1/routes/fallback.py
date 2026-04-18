"""
Traditional KYC Fallback Routes - M19
BFIU Circular No. 29 — Section 3.2

POST /fallback/create              - Create fallback case
POST /fallback/{id}/document       - Upload physical document
POST /fallback/{id}/review/start   - Start document review
POST /fallback/{id}/review/decide  - Approve or reject case
GET  /fallback/{id}                - Get case by case_id
GET  /fallback/session/{sid}       - Get case by session_id
GET  /fallback/queue/pending       - Cases awaiting review
GET  /fallback/stats               - Case statistics
GET  /fallback/document-types      - List required document types
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.fallback_service import (
    create_fallback_case, submit_document, start_review,
    decide_case, get_case, get_case_by_session,
    list_cases, get_stats,
    DOCUMENT_TYPES, TRIGGER_CODES,
    REQUIRED_DOCS_SIMPLIFIED, REQUIRED_DOCS_REGULAR,
)

router = APIRouter(prefix="/fallback", tags=["Traditional KYC Fallback"])


class CreateFallbackRequest(BaseModel):
    session_id:      str
    trigger_code:    str = "MANUAL_TRIGGER"
    agent_id:        str = "N/A"
    institution_id:  str = "N/A"
    kyc_type:        str = "SIMPLIFIED"
    customer_mobile: Optional[str] = None
    customer_name:   Optional[str] = None
    notes:           Optional[str] = None


class DocumentUploadRequest(BaseModel):
    doc_type:    str
    doc_b64:     str
    filename:    str = ""
    uploaded_by: str = "customer"


class ReviewStartRequest(BaseModel):
    reviewer_id: str


class ReviewDecideRequest(BaseModel):
    reviewer_id: str
    decision:    str   # APPROVE | REJECT
    note:        Optional[str] = None


@router.post("/create", status_code=201, operation_id="fallback_create")
def create_fallback(req: CreateFallbackRequest):
    """
    Create traditional KYC fallback case.
    Triggered when eKYC fails technically or EC is unavailable.
    """
    if req.trigger_code not in TRIGGER_CODES:
        raise HTTPException(400, f"Invalid trigger_code. Must be one of: {list(TRIGGER_CODES)}")
    result = create_fallback_case(**req.model_dump())
    return {
        "case":          result["case"],
        "already_exists":result["already_exists"],
        "bfiu_ref":      "BFIU Circular No. 29 — Section 3.2",
    }


@router.post("/{case_id}/document", status_code=201, operation_id="fallback_upload_doc")
def upload_fallback_document(case_id: str, req: DocumentUploadRequest):
    """Upload a physical document for a fallback case."""
    result = submit_document(case_id, req.doc_type, req.doc_b64,
                             req.filename, req.uploaded_by)
    if not result.get("success"):
        raise HTTPException(422, result.get("error","Upload failed"))
    return result


@router.post("/{case_id}/review/start",          operation_id="fallback_review_start")
def fallback_review_start(case_id: str, req: ReviewStartRequest):
    """Agent picks up fallback case for document review."""
    result = start_review(case_id, req.reviewer_id)
    if not result.get("success"):
        raise HTTPException(422, result.get("error","Cannot start review"))
    return result


@router.post("/{case_id}/review/decide",         operation_id="fallback_review_decide")
def fallback_review_decide(case_id: str, req: ReviewDecideRequest):
    """Approve or reject traditional KYC case after document review."""
    result = decide_case(case_id, req.reviewer_id, req.decision, req.note)
    if not result.get("success"):
        raise HTTPException(422, result.get("error","Decision failed"))
    return result


@router.get("/queue/pending",                    operation_id="fallback_queue_pending")
def fallback_pending_queue(limit: int = Query(50, le=200)):
    """Cases awaiting document review."""
    items = list_cases("DOCS_SUBMITTED", limit)
    items += list_cases("UNDER_REVIEW", limit)
    return {"queue": items, "total": len(items)}


@router.get("/stats",                            operation_id="fallback_get_stats")
def fallback_stats():
    """Fallback case statistics by status."""
    s = get_stats()
    return {
        "stats":          s,
        "total":          sum(s.values()),
        "pending_review": s.get("DOCS_SUBMITTED",0) + s.get("UNDER_REVIEW",0),
        "bfiu_ref":       "BFIU Circular No. 29 — Section 3.2",
    }


@router.get("/document-types",                   operation_id="fallback_doc_types")
def fallback_document_types():
    """List all valid document types with requirements."""
    return {
        "document_types":          DOCUMENT_TYPES,
        "required_simplified":     REQUIRED_DOCS_SIMPLIFIED,
        "required_regular":        REQUIRED_DOCS_REGULAR,
        "trigger_codes":           TRIGGER_CODES,
    }


@router.get("/session/{session_id}",             operation_id="fallback_by_session")
def fallback_get_by_session(session_id: str):
    """Get fallback case by original eKYC session ID."""
    case = get_case_by_session(session_id)
    if not case:
        raise HTTPException(404, f"No fallback case for session '{session_id}'")
    return {"case": case}


@router.get("/{case_id}",                        operation_id="fallback_by_id")
def fallback_get_by_id(case_id: str):
    """Get fallback case by case ID."""
    case = get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case '{case_id}' not found")
    return {"case": case}
