"""
File Storage Service - M27
Saves NID images, signatures, customer photos to local filesystem.
Every file saved is tracked in the DB via UploadedFile model.
Configurable storage path — ready for S3/MinIO swap in production.
"""
import os, base64, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from app.db.database import db_session
from app.db.models import UploadedFile

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "../../uploads"))

VALID_CATEGORIES = {
    "nid_front", "nid_back", "signature", "photo",
    "liveness", "fallback_doc", "other",
}

def _now(): return datetime.now(timezone.utc)

def _ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def _row(r) -> dict:
    return {
        "id":            r.id,
        "session_id":    r.session_id,
        "category":      r.category,
        "filename":      r.filename,
        "file_url":      r.file_url,
        "file_size":     r.file_size,
        "sha256":        r.sha256,
        "mime_type":     r.mime_type,
        "uploaded_by":   r.uploaded_by,
        "institution_id":r.institution_id,
        "bfiu_ref":      r.bfiu_ref,
        "created_at":    str(r.created_at),
    }

def save_image(image_b64: str, category: str, session_id: str,
               filename: str = None, uploaded_by: str = "system",
               institution_id: str = "default") -> dict:
    """
    Save a base64 image to disk and record metadata in DB.
    category: nid_front | nid_back | signature | photo | liveness | fallback_doc | other
    Returns: file_url, file_size, sha256, id
    """
    if category not in VALID_CATEGORIES:
        return {"error": f"Invalid category: {category!r}. Must be one of {sorted(VALID_CATEGORIES)}"}

    # Decode base64
    mime_type = "image/jpeg"
    if "," in image_b64:
        header, data = image_b64.split(",", 1)
        if "png" in header:
            ext = "png"; mime_type = "image/png"
        elif "jpeg" in header or "jpg" in header:
            ext = "jpg"; mime_type = "image/jpeg"
        else:
            ext = "jpg"
    else:
        data = image_b64
        ext = "jpg"

    try:
        img_bytes = base64.b64decode(data)
    except Exception as e:
        return {"error": f"Could not decode image: {e}"}

    # Build path: uploads/category/YYYY/MM/session_id_uuid.ext
    now = _now()
    subdir = os.path.join(UPLOAD_DIR, category, str(now.year), f"{now.month:02d}")
    _ensure_dir(subdir)
    fname = filename or f"{session_id}_{str(uuid.uuid4())[:8]}.{ext}"
    fpath = os.path.join(subdir, fname)

    with open(fpath, "wb") as f:
        f.write(img_bytes)

    sha256   = hashlib.sha256(img_bytes).hexdigest()
    rel_path = os.path.relpath(fpath, UPLOAD_DIR)
    file_url = f"/uploads/{rel_path.replace(os.sep, '/')}"
    file_id  = str(uuid.uuid4())

    # Persist to DB
    try:
        with db_session() as db:
            row = UploadedFile(
                id=file_id, session_id=session_id, category=category,
                filename=fname, file_url=file_url, file_path=fpath,
                file_size=len(img_bytes), sha256=sha256, mime_type=mime_type,
                uploaded_by=uploaded_by, institution_id=institution_id,
                bfiu_ref="BFIU Circular No. 29", created_at=now,
            )
            db.add(row)
    except Exception as e:
        print(f"[FILE STORAGE] DB write failed: {e}")

    return {
        "id":         file_id,
        "file_url":   file_url,
        "file_path":  fpath,
        "file_size":  len(img_bytes),
        "sha256":     sha256,
        "mime_type":  mime_type,
        "category":   category,
        "session_id": session_id,
        "filename":   fname,
    }

def get_file(file_id: str) -> Optional[dict]:
    with db_session() as db:
        r = db.query(UploadedFile).filter_by(id=file_id).first()
        return _row(r) if r else None

def list_files(session_id: str = None, category: str = None, limit: int = 50) -> list:
    with db_session() as db:
        q = db.query(UploadedFile)
        if session_id: q = q.filter(UploadedFile.session_id == session_id)
        if category:   q = q.filter(UploadedFile.category == category)
        return [_row(r) for r in q.order_by(UploadedFile.created_at.desc()).limit(limit).all()]

def delete_file(file_id: str) -> dict:
    with db_session() as db:
        r = db.query(UploadedFile).filter_by(id=file_id).first()
        if not r:
            return {"success": False, "error": "File not found"}
        fpath = r.file_path
        db.delete(r)
    # Delete from disk
    try:
        if fpath and os.path.exists(fpath):
            os.remove(fpath)
    except Exception as e:
        return {"success": True, "warning": f"DB record deleted but disk removal failed: {e}"}
    return {"success": True, "deleted_id": file_id}

def get_upload_stats() -> dict:
    total_files_disk = 0
    total_size_disk  = 0
    try:
        for root, dirs, files in os.walk(UPLOAD_DIR):
            for f in files:
                total_files_disk += 1
                total_size_disk  += os.path.getsize(os.path.join(root, f))
    except Exception:
        pass
    with db_session() as db:
        total_db = db.query(UploadedFile).count()
        by_category = {}
        for cat in VALID_CATEGORIES:
            by_category[cat] = db.query(UploadedFile).filter_by(category=cat).count()
    return {
        "total_files_db":   total_db,
        "total_files_disk": total_files_disk,
        "total_size_mb":    round(total_size_disk / 1024 / 1024, 2),
        "by_category":      by_category,
        "upload_dir":       UPLOAD_DIR,
        "bfiu_ref":         "BFIU Circular No. 29",
    }

# ── Convenience wrappers ────────────────────────────────────────────────
def save_nid_front(image_b64: str, session_id: str, **kwargs) -> dict:
    return save_image(image_b64, "nid_front", session_id, **kwargs)

def save_nid_back(image_b64: str, session_id: str, **kwargs) -> dict:
    return save_image(image_b64, "nid_back", session_id, **kwargs)

def save_signature(image_b64: str, session_id: str, **kwargs) -> dict:
    return save_image(image_b64, "signature", session_id,
                      filename=f"{session_id}_sig.png", **kwargs)

def save_customer_photo(image_b64: str, session_id: str, **kwargs) -> dict:
    return save_image(image_b64, "photo", session_id,
                      filename=f"{session_id}_photo.jpg", **kwargs)
