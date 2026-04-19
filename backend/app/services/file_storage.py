"""
File Storage Service - M27
Saves NID images, signatures, customer photos to local filesystem.
Configurable storage path — ready for S3/MinIO swap in production.
"""
import os, base64, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "../../uploads"))

def _ensure_dir(path:str):
    Path(path).mkdir(parents=True, exist_ok=True)

def save_image(image_b64:str, category:str, session_id:str, filename:str=None) -> dict:
    """
    Save a base64 image to disk.
    category: nid_front | nid_back | signature | photo | liveness
    Returns: file_url (relative path), file_size, sha256
    """
    # Decode base64
    if "," in image_b64:
        header, data = image_b64.split(",", 1)
        ext = "jpg" if "jpeg" in header else "png"
    else:
        data = image_b64
        ext = "jpg"

    try:
        img_bytes = base64.b64decode(data)
    except Exception as e:
        return {"error": f"Could not decode image: {e}"}

    # Build path: uploads/category/YYYY/MM/session_id_uuid.ext
    now = datetime.now(timezone.utc)
    subdir = os.path.join(UPLOAD_DIR, category, str(now.year), f"{now.month:02d}")
    _ensure_dir(subdir)

    fname = filename or f"{session_id}_{str(uuid.uuid4())[:8]}.{ext}"
    fpath = os.path.join(subdir, fname)

    with open(fpath, "wb") as f:
        f.write(img_bytes)

    sha256 = hashlib.sha256(img_bytes).hexdigest()
    rel_path = os.path.relpath(fpath, UPLOAD_DIR)
    file_url = f"/uploads/{rel_path.replace(os.sep, '/')}"

    return {
        "file_url":  file_url,
        "file_path": fpath,
        "file_size": len(img_bytes),
        "sha256":    sha256,
        "category":  category,
        "session_id":session_id,
    }

def save_nid_front(image_b64:str, session_id:str) -> dict:
    return save_image(image_b64, "nid_front", session_id)

def save_nid_back(image_b64:str, session_id:str) -> dict:
    return save_image(image_b64, "nid_back", session_id)

def save_signature(image_b64:str, session_id:str) -> dict:
    return save_image(image_b64, "signatures", session_id, f"{session_id}_sig.png")

def save_customer_photo(image_b64:str, session_id:str) -> dict:
    return save_image(image_b64, "photos", session_id, f"{session_id}_photo.jpg")

def get_upload_stats() -> dict:
    total_files = 0
    total_size = 0
    try:
        for root, dirs, files in os.walk(UPLOAD_DIR):
            for f in files:
                total_files += 1
                total_size += os.path.getsize(os.path.join(root, f))
    except Exception:
        pass
    return {
        "total_files": total_files,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "upload_dir": UPLOAD_DIR,
    }
