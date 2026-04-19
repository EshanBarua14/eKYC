"""
File Storage Routes - M27
POST /files/upload         - Upload a file (base64)
GET  /files/{file_id}      - Get file metadata
GET  /files/session/{sid}  - List files for a session
GET  /files/stats          - Storage statistics
DELETE /files/{file_id}    - Delete a file
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.file_storage import (
    save_image, get_file, list_files, delete_file,
    get_upload_stats, VALID_CATEGORIES,
)

router = APIRouter(prefix="/files", tags=["File Storage"])


class FileUploadRequest(BaseModel):
    image_b64:      str
    category:       str
    session_id:     str
    filename:       Optional[str] = None
    uploaded_by:    str = "system"
    institution_id: str = "default"


@router.post("/upload", status_code=201, operation_id="file_upload")
async def upload_file(req: FileUploadRequest):
    """Upload a base64-encoded image and save to disk + DB."""
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Must be one of: {sorted(VALID_CATEGORIES)}")
    result = save_image(
        image_b64=req.image_b64, category=req.category,
        session_id=req.session_id, filename=req.filename,
        uploaded_by=req.uploaded_by, institution_id=req.institution_id,
    )
    if result.get("error"):
        raise HTTPException(422, result["error"])
    return {"file": result, "bfiu_ref": "BFIU Circular No. 29"}


@router.get("/stats", operation_id="file_stats")
async def file_stats():
    """Storage statistics — total files, size, breakdown by category."""
    return get_upload_stats()


@router.get("/session/{session_id}", operation_id="files_by_session")
async def files_by_session(
    session_id: str,
    category: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """List all files uploaded for a session."""
    files = list_files(session_id=session_id, category=category, limit=limit)
    return {"files": files, "total": len(files), "session_id": session_id}


@router.get("/categories", operation_id="file_categories")
async def file_categories():
    """List valid upload categories."""
    return {"categories": sorted(VALID_CATEGORIES), "bfiu_ref": "BFIU Circular No. 29"}


@router.get("/{file_id}", operation_id="file_get")
async def get_file_metadata(file_id: str):
    """Get file metadata by ID."""
    f = get_file(file_id)
    if not f:
        raise HTTPException(404, f"File {file_id!r} not found")
    return {"file": f}


@router.delete("/{file_id}", operation_id="file_delete")
async def delete_file_record(file_id: str):
    """Delete a file record and remove from disk."""
    result = delete_file(file_id)
    if not result.get("success"):
        raise HTTPException(404, result.get("error", "File not found"))
    return result
