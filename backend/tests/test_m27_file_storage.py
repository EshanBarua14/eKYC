"""
test_m27_file_storage.py - M27 File Storage Service
Tests: upload, get, list by session, stats, delete, categories, validation
"""
import base64
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/files"

# Minimal valid 1x1 red pixel JPEG in base64
TINY_JPEG = (
    "data:image/jpeg;base64,"
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
    "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
    "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
    "MjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAA"
    "AAAAAAAAAAAAAAAAAP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAA"
    "AAAA/9oADAMBAAIRAxEAPwCwABmX/9k="
)

TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg=="
)

def upload(category="nid_front", session_id="sess_file_01", image=TINY_JPEG):
    return client.post(f"{BASE}/upload", json={
        "image_b64":   image,
        "category":    category,
        "session_id":  session_id,
        "uploaded_by": "agent_01",
        "institution_id": "inst_01",
    })

# ══════════════════════════════════════════════════════════════════════════
# 1. Upload (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestUpload:
    def test_upload_returns_201(self):
        r = upload(session_id="sess_up_01")
        assert r.status_code == 201

    def test_upload_has_file_id(self):
        r = upload(session_id="sess_up_02")
        assert "id" in r.json()["file"]
        assert len(r.json()["file"]["id"]) == 36

    def test_upload_has_file_url(self):
        r = upload(session_id="sess_up_03")
        assert r.json()["file"]["file_url"].startswith("/uploads/")

    def test_upload_has_sha256(self):
        r = upload(session_id="sess_up_04")
        assert len(r.json()["file"]["sha256"]) == 64

    def test_upload_has_file_size(self):
        r = upload(session_id="sess_up_05")
        assert r.json()["file"]["file_size"] > 0

    def test_upload_png_accepted(self):
        r = upload(session_id="sess_up_06", image=TINY_PNG)
        assert r.status_code == 201
        assert r.json()["file"]["mime_type"] == "image/png"

    def test_upload_invalid_category_400(self):
        r = client.post(f"{BASE}/upload", json={
            "image_b64": TINY_JPEG, "category": "INVALID_CAT",
            "session_id": "sess_up_07",
        })
        assert r.status_code == 400

    def test_upload_invalid_base64_422(self):
        r = client.post(f"{BASE}/upload", json={
            "image_b64": "not_valid_base64!!!",
            "category": "nid_front", "session_id": "sess_up_08",
        })
        assert r.status_code == 422

    def test_upload_all_categories(self):
        categories = ["nid_front","nid_back","signature","photo","liveness","fallback_doc","other"]
        for i, cat in enumerate(categories):
            r = upload(category=cat, session_id=f"sess_cat_{i:02d}")
            assert r.status_code == 201, f"Failed for category: {cat}"

# ══════════════════════════════════════════════════════════════════════════
# 2. Get by ID (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestGetFile:
    def test_get_file_200(self):
        r = upload(session_id="sess_get_f_01")
        file_id = r.json()["file"]["id"]
        r2 = client.get(f"{BASE}/{file_id}")
        assert r2.status_code == 200
        assert r2.json()["file"]["id"] == file_id

    def test_get_file_has_metadata(self):
        r = upload(session_id="sess_get_f_02", category="nid_back")
        file_id = r.json()["file"]["id"]
        r2 = client.get(f"{BASE}/{file_id}")
        f = r2.json()["file"]
        for key in ["id","session_id","category","file_url","sha256","file_size"]:
            assert key in f, f"Missing key: {key}"

    def test_get_nonexistent_404(self):
        r = client.get(f"{BASE}/nonexistent-id-xyz")
        assert r.status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 3. List by session (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestListBySession:
    def test_list_session_200(self):
        upload(session_id="sess_list_01", category="nid_front")
        upload(session_id="sess_list_01", category="nid_back")
        r = client.get(f"{BASE}/session/sess_list_01")
        assert r.status_code == 200

    def test_list_session_returns_all_files(self):
        upload(session_id="sess_list_02", category="nid_front")
        upload(session_id="sess_list_02", category="signature")
        r = client.get(f"{BASE}/session/sess_list_02")
        assert r.json()["total"] >= 2

    def test_list_session_filter_by_category(self):
        upload(session_id="sess_list_03", category="nid_front")
        upload(session_id="sess_list_03", category="photo")
        r = client.get(f"{BASE}/session/sess_list_03?category=nid_front")
        assert all(f["category"] == "nid_front" for f in r.json()["files"])

    def test_list_empty_session_returns_empty(self):
        r = client.get(f"{BASE}/session/sess_nonexistent_xyz999")
        assert r.status_code == 200
        assert r.json()["total"] == 0

# ══════════════════════════════════════════════════════════════════════════
# 4. Delete (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestDelete:
    def test_delete_200(self):
        r = upload(session_id="sess_del_01")
        file_id = r.json()["file"]["id"]
        r2 = client.delete(f"{BASE}/{file_id}")
        assert r2.status_code == 200
        assert r2.json()["success"] is True

    def test_delete_removes_from_db(self):
        r = upload(session_id="sess_del_02")
        file_id = r.json()["file"]["id"]
        client.delete(f"{BASE}/{file_id}")
        r2 = client.get(f"{BASE}/{file_id}")
        assert r2.status_code == 404

    def test_delete_nonexistent_404(self):
        r = client.delete(f"{BASE}/nonexistent-del-xyz")
        assert r.status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 5. Stats & Categories (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestStatsAndCategories:
    def test_stats_200(self):
        r = client.get(f"{BASE}/stats")
        assert r.status_code == 200

    def test_stats_has_required_keys(self):
        r = client.get(f"{BASE}/stats")
        d = r.json()
        for key in ["total_files_db","total_files_disk","total_size_mb","by_category"]:
            assert key in d, f"Missing key: {key}"

    def test_categories_200(self):
        r = client.get(f"{BASE}/categories")
        assert r.status_code == 200

    def test_categories_has_all_types(self):
        r = client.get(f"{BASE}/categories")
        cats = r.json()["categories"]
        for c in ["nid_front","nid_back","signature","photo","liveness"]:
            assert c in cats, f"Missing category: {c}"
