# M27 File Storage Wiring — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Built and wired M27 file storage — every uploaded file now tracked in DB.
Tests: 23 new tests added, 721/721 passing (was 698).

## What was built

### app/db/models_platform.py
- Added UploadedFile SQLAlchemy model
- Columns: id, session_id, category, filename, file_url, file_path,
  file_size, sha256, mime_type, uploaded_by, institution_id, bfiu_ref, created_at

### app/db/models/__init__.py
- Exported UploadedFile

### app/services/file_storage.py
- save_image(): validates category, decodes base64, saves to disk, persists to DB
- get_file(): get metadata by file ID
- list_files(): filter by session_id and/or category
- delete_file(): removes DB record + disk file
- get_upload_stats(): disk + DB counts, breakdown by category
- Convenience wrappers: save_nid_front, save_nid_back, save_signature, save_customer_photo
- VALID_CATEGORIES: nid_front, nid_back, signature, photo, liveness, fallback_doc, other

### app/api/v1/routes/file_storage.py
- POST /files/upload       - Upload base64 image (201)
- GET  /files/{id}         - Get file metadata
- GET  /files/session/{sid} - List files for session
- GET  /files/stats        - Storage stats
- GET  /files/categories   - Valid categories
- DELETE /files/{id}       - Delete file

### app/api/v1/router.py
- Added file_storage_router
- Removed duplicate imports/includes (notification, outcome, fallback, cmi, bfiu_report)

### tests/test_m27_file_storage.py
- 23 tests across: Upload, GetFile, ListBySession, Delete, StatsAndCategories
