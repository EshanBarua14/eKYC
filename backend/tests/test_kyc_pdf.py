"""
test_kyc_pdf.py - M15 Digital KYC PDF Generator
Tests: PDF service, generate endpoint, download endpoint, list endpoint
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.pdf_service import generate_kyc_pdf

client = TestClient(app)
BASE   = "/api/v1/kyc"

SAMPLE = {
    "session_id":      "sess_pdf_test_01",
    "verdict":         "MATCHED",
    "confidence":      87.5,
    "timestamp":       "2026-04-18T10:00:00Z",
    "processing_ms":   320,
    "full_name":       "Md. Rahman Hossain",
    "date_of_birth":   "1985-06-15",
    "mobile":          "01712345678",
    "fathers_name":    "Abdul Rahman",
    "mothers_name":    "Fatema Begum",
    "gender":          "Male",
    "nationality":     "Bangladeshi",
    "profession":      "Business",
    "present_address": "Dhaka, Bangladesh",
    "kyc_type":        "SIMPLIFIED",
    "institution_type":"INSURANCE",
    "risk_grade":      "LOW",
    "risk_score":      4,
    "edd_required":    False,
    "status":          "APPROVED",
    "pep_flag":        False,
    "unscr_checked":   True,
    "screening_result":"CLEAR",
    "liveness_passed": True,
    "liveness_score":  5,
    "liveness_max":    5,
    "ssim_score":      72.3,
    "orb_score":       65.1,
    "histogram_score": 81.4,
    "pixel_score":     58.9,
    "agent_id":        "agent_01",
    "institution_id":  "inst_01",
    "geolocation":     "23.8103,90.4125",
}

# ══════════════════════════════════════════════════════════════════════════
# 1. PDF Service unit tests (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestPDFService:
    def test_generate_returns_bytes(self):
        b = generate_kyc_pdf(**{k:v for k,v in SAMPLE.items()})
        assert isinstance(b, bytes)
        assert len(b) > 1000

    def test_pdf_starts_with_pdf_header(self):
        b = generate_kyc_pdf(**{k:v for k,v in SAMPLE.items()})
        assert b[:4] == b"%PDF"

    def test_pdf_review_verdict(self):
        data = {**SAMPLE, "session_id":"sess_review","verdict":"REVIEW","confidence":42.0}
        b = generate_kyc_pdf(**{k:v for k,v in data.items()})
        assert b[:4] == b"%PDF"
        assert len(b) > 1000

    def test_pdf_failed_verdict(self):
        data = {**SAMPLE, "session_id":"sess_failed","verdict":"FAILED","confidence":18.0}
        b = generate_kyc_pdf(**{k:v for k,v in data.items()})
        assert b[:4] == b"%PDF"

# ══════════════════════════════════════════════════════════════════════════
# 2. Generate endpoint (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestGenerateEndpoint:
    def test_generate_returns_201(self):
        r = client.post(f"{BASE}/pdf/generate", json=SAMPLE)
        assert r.status_code == 201

    def test_generate_response_has_fields(self):
        data = {**SAMPLE, "session_id":"sess_fields_01"}
        r = client.post(f"{BASE}/pdf/generate", json=data)
        assert r.status_code == 201
        d = r.json()
        for key in ["session_id","generated_at","size_bytes","download_url"]:
            assert key in d, f"Missing: {key}"

    def test_generate_size_bytes_positive(self):
        data = {**SAMPLE, "session_id":"sess_size_01"}
        r = client.post(f"{BASE}/pdf/generate", json=data)
        assert r.json()["size_bytes"] > 1000

    def test_generate_download_url_correct(self):
        data = {**SAMPLE, "session_id":"sess_url_01"}
        r = client.post(f"{BASE}/pdf/generate", json=data)
        assert r.json()["download_url"] == f"{BASE}/profile/sess_url_01/pdf"

    def test_generate_invalid_verdict_400(self):
        data = {**SAMPLE, "session_id":"sess_bad","verdict":"INVALID"}
        r = client.post(f"{BASE}/pdf/generate", json=data)
        assert r.status_code == 400

# ══════════════════════════════════════════════════════════════════════════
# 3. Download endpoint (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestDownloadEndpoint:
    def test_download_returns_pdf_bytes(self):
        sid = "sess_dl_01"
        client.post(f"{BASE}/pdf/generate", json={**SAMPLE,"session_id":sid})
        r = client.get(f"{BASE}/profile/{sid}/pdf")
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_download_content_type_pdf(self):
        sid = "sess_dl_02"
        client.post(f"{BASE}/pdf/generate", json={**SAMPLE,"session_id":sid})
        r = client.get(f"{BASE}/profile/{sid}/pdf")
        assert "application/pdf" in r.headers["content-type"]

    def test_download_content_disposition(self):
        sid = "sess_dl_03"
        client.post(f"{BASE}/pdf/generate", json={**SAMPLE,"session_id":sid})
        r = client.get(f"{BASE}/profile/{sid}/pdf")
        assert sid in r.headers["content-disposition"]

    def test_download_nonexistent_404(self):
        r = client.get(f"{BASE}/profile/nonexistent_session/pdf")
        assert r.status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 4. List endpoint (2 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestListEndpoint:
    def test_list_pdfs_200(self):
        assert client.get(f"{BASE}/pdf/list").status_code == 200

    def test_list_pdfs_after_generate(self):
        client.post(f"{BASE}/pdf/generate", json={**SAMPLE,"session_id":"sess_list_01"})
        r = client.get(f"{BASE}/pdf/list")
        d = r.json()
        assert "pdfs" in d and "total" in d
        assert d["total"] >= 1
        assert any(p["session_id"]=="sess_list_01" for p in d["pdfs"])
