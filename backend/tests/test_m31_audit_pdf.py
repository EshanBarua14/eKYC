"""
test_m31_audit_pdf.py - M31 Audit Export PDF
Tests: PDF generation, content, auth, session export, custom export, BFIU compliance
"""
import base64
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.audit_service import log_event, reset_audit_log

client = TestClient(app)
BASE = "/api/v1/audit"
AUTH = "/api/v1/auth"

from tests.test_helpers import setup_totp_and_login

def get_admin_token():
    return setup_totp_and_login(client, "admin_m31@test.com", "ADMIN")

def get_auditor_token():
    return setup_totp_and_login(client, "auditor_m31@test.com", "AUDITOR")

def ah(): return {"Authorization": f"Bearer {get_admin_token()}"}
def audh(): return {"Authorization": f"Bearer {get_auditor_token()}"}

def seed_audit_entries(n=5, session_id="sess_pdf_test"):
    for i in range(n):
        log_event("USER_CREATED","User",actor_id=f"actor_{i}",session_id=session_id)

# ══════════════════════════════════════════════════════════════════════════
# 1. Auth required (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAuthRequired:
    def test_pdf_export_requires_auth(self):
        r = client.get(f"{BASE}/export/pdf")
        assert r.status_code == 403

    def test_session_pdf_requires_auth(self):
        r = client.get(f"{BASE}/export/pdf/session/test_session")
        assert r.status_code == 403

    def test_custom_pdf_requires_auth(self):
        r = client.post(f"{BASE}/export/pdf/custom", json={})
        assert r.status_code == 403

# ══════════════════════════════════════════════════════════════════════════
# 2. PDF generation (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestPDFGeneration:
    def test_export_pdf_200(self):
        seed_audit_entries()
        r = client.get(f"{BASE}/export/pdf", headers=ah())
        assert r.status_code == 200

    def test_export_pdf_content_type(self):
        seed_audit_entries()
        r = client.get(f"{BASE}/export/pdf", headers=ah())
        assert r.headers["content-type"] == "application/pdf"

    def test_export_pdf_has_content_disposition(self):
        seed_audit_entries()
        r = client.get(f"{BASE}/export/pdf", headers=ah())
        assert "attachment" in r.headers.get("content-disposition","")
        assert ".pdf" in r.headers.get("content-disposition","")

    def test_export_pdf_is_valid_pdf(self):
        seed_audit_entries()
        r = client.get(f"{BASE}/export/pdf", headers=ah())
        assert r.content[:4] == b"%PDF"

    def test_export_pdf_has_nonzero_size(self):
        seed_audit_entries()
        r = client.get(f"{BASE}/export/pdf", headers=ah())
        assert len(r.content) > 1000

    def test_auditor_can_export_pdf(self):
        seed_audit_entries()
        r = client.get(f"{BASE}/export/pdf", headers=audh())
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

# ══════════════════════════════════════════════════════════════════════════
# 3. Session PDF export (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestSessionPDF:
    def test_session_pdf_200(self):
        sid = "sess_m31_pdf_01"
        log_event("SESSION_CREATED","LivenessSession",session_id=sid)
        r = client.get(f"{BASE}/export/pdf/session/{sid}", headers=ah())
        assert r.status_code == 200

    def test_session_pdf_is_valid_pdf(self):
        sid = "sess_m31_pdf_02"
        log_event("FACE_VERIFY_MATCHED","VerificationResult",session_id=sid)
        r = client.get(f"{BASE}/export/pdf/session/{sid}", headers=ah())
        assert r.content[:4] == b"%PDF"

    def test_session_pdf_content_type(self):
        sid = "sess_m31_pdf_03"
        log_event("USER_CREATED","User",session_id=sid)
        r = client.get(f"{BASE}/export/pdf/session/{sid}", headers=ah())
        assert r.headers["content-type"] == "application/pdf"

    def test_session_pdf_404_no_entries(self):
        r = client.get(f"{BASE}/export/pdf/session/nonexistent_xyz_999", headers=ah())
        assert r.status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 4. Custom PDF export (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestCustomPDF:
    def test_custom_export_201(self):
        seed_audit_entries()
        r = client.post(f"{BASE}/export/pdf/custom",
                        json={"report_title":"Custom Audit","generated_by":"test_officer"},
                        headers=ah())
        assert r.status_code == 201

    def test_custom_export_has_pdf_b64(self):
        seed_audit_entries()
        r = client.post(f"{BASE}/export/pdf/custom", json={}, headers=ah())
        assert "pdf_b64" in r.json()
        assert len(r.json()["pdf_b64"]) > 100

    def test_custom_export_pdf_b64_is_valid_pdf(self):
        seed_audit_entries()
        r = client.post(f"{BASE}/export/pdf/custom", json={}, headers=ah())
        pdf_bytes = base64.b64decode(r.json()["pdf_b64"])
        assert pdf_bytes[:4] == b"%PDF"

    def test_custom_export_has_entry_count(self):
        seed_audit_entries(3)
        r = client.post(f"{BASE}/export/pdf/custom", json={}, headers=ah())
        assert "entry_count" in r.json()
        assert r.json()["entry_count"] >= 3

    def test_custom_export_has_bfiu_ref(self):
        r = client.post(f"{BASE}/export/pdf/custom", json={}, headers=ah())
        assert "bfiu_ref" in r.json()
        assert "BFIU" in r.json()["bfiu_ref"]

# ══════════════════════════════════════════════════════════════════════════
# 5. PDF service unit tests (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestPDFService:
    def test_generate_pdf_returns_bytes(self):
        from app.services.audit_pdf_service import generate_audit_pdf
        pdf = generate_audit_pdf(entries=[], report_title="Test")
        assert isinstance(pdf, bytes)

    def test_generate_pdf_starts_with_pdf_header(self):
        from app.services.audit_pdf_service import generate_audit_pdf
        pdf = generate_audit_pdf(entries=[])
        assert pdf[:4] == b"%PDF"

    def test_generate_pdf_with_entries(self):
        from app.services.audit_pdf_service import generate_audit_pdf
        entries = [{"event_type":"USER_CREATED","entity_type":"User",
                    "actor_id":"admin-01","session_id":"sess-01",
                    "timestamp":"2026-04-19T10:00:00"}]
        pdf = generate_audit_pdf(entries=entries, report_title="Test Report")
        assert len(pdf) > 2000

    def test_generate_session_pdf(self):
        from app.services.audit_pdf_service import generate_session_audit_pdf
        entries = [{"event_type":"SESSION_CREATED","entity_type":"Session",
                    "actor_id":"agent-01","session_id":"sess-test",
                    "timestamp":"2026-04-19T10:00:00"}]
        pdf = generate_session_audit_pdf("sess-test", entries)
        assert pdf[:4] == b"%PDF"
