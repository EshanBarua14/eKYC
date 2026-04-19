"""
Institution Onboarding Routes - M33
POST /institutions/onboard/apply      - Submit application
GET  /institutions/onboard/applications - List applications
GET  /institutions/onboard/{app_id}   - Get application
POST /institutions/onboard/{app_id}/review  - Start review
POST /institutions/onboard/{app_id}/note    - Add review note
POST /institutions/onboard/{app_id}/approve - Approve
POST /institutions/onboard/{app_id}/reject  - Reject
POST /institutions/onboard/{inst_id}/activate - Activate
POST /institutions/onboard/{inst_id}/suspend  - Suspend
GET  /institutions/onboard/stats      - Pipeline stats
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from app.middleware.rbac import require_admin, require_admin_or_auditor
from app.services.institution_onboarding_service import (
    submit_application, get_application, list_applications,
    start_review, add_review_note, approve_application,
    reject_application, activate_institution, suspend_institution,
    get_onboarding_stats, reset_applications,
)

router = APIRouter(prefix="/institutions/onboard", tags=["Institution Onboarding"])

class ApplicationRequest(BaseModel):
    name:             str
    short_code:       str
    institution_type: str = "insurance"
    contact_email:    str
    contact_phone:    str
    address:          str = ""
    license_number:   str = ""
    ip_whitelist:     List[str] = []

class ReviewRequest(BaseModel):
    note: Optional[str] = ""

class ApprovalRequest(BaseModel):
    note: Optional[str] = ""

class RejectionRequest(BaseModel):
    reason: str

class NoteRequest(BaseModel):
    note: str

class SuspendRequest(BaseModel):
    reason: str = ""

@router.get("/stats", operation_id="onboard_stats")
async def onboarding_stats(cu: dict = Depends(require_admin_or_auditor)):
    return get_onboarding_stats()

@router.post("/apply", status_code=201, operation_id="onboard_apply")
async def apply_for_onboarding(req: ApplicationRequest):
    """Submit institution onboarding application — public endpoint."""
    result = submit_application(
        name=req.name, short_code=req.short_code,
        institution_type=req.institution_type,
        contact_email=req.contact_email,
        contact_phone=req.contact_phone,
        address=req.address, license_number=req.license_number,
        ip_whitelist=req.ip_whitelist,
    )
    if result.get("error"):
        raise HTTPException(409, result["error"])
    return result

@router.get("/applications", operation_id="onboard_list")
async def list_all_applications(
    status: Optional[str] = None,
    cu: dict = Depends(require_admin_or_auditor),
):
    return {"applications": list_applications(status), "total": len(list_applications(status))}

@router.get("/{app_id}", operation_id="onboard_get")
async def get_application_detail(
    app_id: str,
    cu: dict = Depends(require_admin_or_auditor),
):
    app = get_application(app_id)
    if not app: raise HTTPException(404, f"Application {app_id!r} not found")
    return {"application": app}

@router.post("/{app_id}/review", operation_id="onboard_review")
async def review_application(
    app_id: str, req: ReviewRequest,
    cu: dict = Depends(require_admin),
):
    result = start_review(app_id, cu.get("sub","admin"), req.note or "")
    if result.get("error"): raise HTTPException(422, result["error"])
    return result

@router.post("/{app_id}/note", operation_id="onboard_note")
async def add_note(
    app_id: str, req: NoteRequest,
    cu: dict = Depends(require_admin),
):
    result = add_review_note(app_id, cu.get("sub","admin"), req.note)
    if result.get("error"): raise HTTPException(404, result["error"])
    return result

@router.post("/{app_id}/approve", status_code=201, operation_id="onboard_approve")
async def approve(
    app_id: str, req: ApprovalRequest,
    cu: dict = Depends(require_admin),
):
    result = approve_application(app_id, cu.get("sub","admin"))
    if result.get("error"): raise HTTPException(422, result["error"])
    return result

@router.post("/{app_id}/reject", operation_id="onboard_reject")
async def reject(
    app_id: str, req: RejectionRequest,
    cu: dict = Depends(require_admin),
):
    result = reject_application(app_id, cu.get("sub","admin"), req.reason)
    if result.get("error"): raise HTTPException(422, result["error"])
    return result

@router.post("/{institution_id}/activate", operation_id="onboard_activate")
async def activate(
    institution_id: str,
    cu: dict = Depends(require_admin),
):
    result = activate_institution(institution_id)
    if result.get("error"): raise HTTPException(404, result["error"])
    return result

@router.post("/{institution_id}/suspend", operation_id="onboard_suspend")
async def suspend(
    institution_id: str, req: SuspendRequest,
    cu: dict = Depends(require_admin),
):
    result = suspend_institution(institution_id, req.reason)
    if result.get("error"): raise HTTPException(404, result["error"])
    return result
