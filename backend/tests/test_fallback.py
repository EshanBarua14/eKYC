"""
test_fallback.py - M19 Traditional KYC Fallback Handler
Tests: create, document upload, review flow, stats, document types
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/fallback"

def make_case(session_id, trigger="NID_API_UNAVAILABLE", kyc_type="SIMPLIFIED"):
    r = client.post(f"{BASE}/create", json={
        "session_id":     session_id,
        "trigger_code":   trigger,
        "agent_id":       "agent_01",
        "institution_id": "inst_01",
        "kyc_type":       kyc_type,
        "customer_name":  "Test Customer",
        "customer_mobile":"01712345678",
    })
    return r

def upload_doc(case_id, doc_type):
    return client.post(f"{BASE}/{case_id}/document", json={
        "doc_type": doc_type, "doc_b64": "base64encodeddata==",
        "filename": f"{doc_type.lower()}.jpg", "uploaded_by": "customer",
    })

def upload_all_docs(case_id, kyc_type="SIMPLIFIED"):
    docs = ["NID_FRONT","NID_BACK","PHOTO","SIGNATURE"]
    if kyc_type == "REGULAR":
        docs += ["UTILITY_BILL","INCOME_PROOF"]
    for d in docs:
        upload_doc(case_id, d)

# ══════════════════════════════════════════════════════════════════════════
# 1. Create Fallback Case (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestCreateFallback:
    def test_create_201(self):
        r = make_case("sess_fb_c1")
        assert r.status_code == 201

    def test_create_has_case_id(self):
        r = make_case("sess_fb_c2")
        assert "case_id" in r.json()["case"]
        assert r.json()["case"]["case_id"].startswith("FKYC-")

    def test_create_initial_status_initiated(self):
        r = make_case("sess_fb_c3")
        assert r.json()["case"]["status"] == "INITIATED"

    def test_create_sets_required_docs_simplified(self):
        r = make_case("sess_fb_c4", kyc_type="SIMPLIFIED")
        required = r.json()["case"]["required_docs"]
        assert "NID_FRONT" in required
        assert "NID_BACK"  in required
        assert "PHOTO"     in required
        assert "SIGNATURE" in required

    def test_create_sets_required_docs_regular(self):
        r = make_case("sess_fb_c5", kyc_type="REGULAR")
        required = r.json()["case"]["required_docs"]
        assert "UTILITY_BILL"  in required
        assert "INCOME_PROOF"  in required

    def test_create_duplicate_returns_existing(self):
        make_case("sess_fb_dup")
        r = make_case("sess_fb_dup")
        assert r.status_code == 201
        assert r.json()["already_exists"] is True

    def test_create_invalid_trigger_400(self):
        r = client.post(f"{BASE}/create", json={
            "session_id":"sess_fb_bad","trigger_code":"UNKNOWN_TRIGGER"})
        assert r.status_code == 400

# ══════════════════════════════════════════════════════════════════════════
# 2. Document Upload (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestDocumentUpload:
    def test_upload_doc_201(self):
        r = make_case("sess_fb_d1")
        cid = r.json()["case"]["case_id"]
        r2 = upload_doc(cid, "NID_FRONT")
        assert r2.status_code == 201
        assert r2.json()["success"] is True

    def test_upload_removes_from_missing(self):
        r = make_case("sess_fb_d2")
        cid = r.json()["case"]["case_id"]
        r2 = upload_doc(cid, "NID_FRONT")
        assert "NID_FRONT" not in r2.json()["missing_docs"]

    def test_all_docs_submitted_changes_status(self):
        r = make_case("sess_fb_d3")
        cid = r.json()["case"]["case_id"]
        upload_all_docs(cid)
        r2 = client.get(f"{BASE}/{cid}")
        assert r2.json()["case"]["status"] == "DOCS_SUBMITTED"

    def test_upload_invalid_doc_type_422(self):
        r = make_case("sess_fb_d4")
        cid = r.json()["case"]["case_id"]
        r2 = client.post(f"{BASE}/{cid}/document",
                         json={"doc_type":"INVALID_DOC","doc_b64":"abc"})
        assert r2.status_code == 422

    def test_upload_to_nonexistent_case_422(self):
        r = client.post(f"{BASE}/FKYC-NOTEXIST/document",
                        json={"doc_type":"NID_FRONT","doc_b64":"abc"})
        assert r.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 3. Review Flow (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestReviewFlow:
    def _setup_ready_case(self, sid):
        r = make_case(sid)
        cid = r.json()["case"]["case_id"]
        upload_all_docs(cid)
        return cid

    def test_start_review(self):
        cid = self._setup_ready_case("sess_fb_r1")
        r = client.post(f"{BASE}/{cid}/review/start",
                        json={"reviewer_id":"checker_01"})
        assert r.status_code == 200
        assert r.json()["case"]["status"] == "UNDER_REVIEW"

    def test_approve_case(self):
        cid = self._setup_ready_case("sess_fb_r2")
        client.post(f"{BASE}/{cid}/review/start", json={"reviewer_id":"c1"})
        r = client.post(f"{BASE}/{cid}/review/decide",
                        json={"reviewer_id":"c1","decision":"APPROVE","note":"All docs verified"})
        assert r.status_code == 200
        assert r.json()["case"]["status"] == "APPROVED"

    def test_reject_case(self):
        cid = self._setup_ready_case("sess_fb_r3")
        client.post(f"{BASE}/{cid}/review/start", json={"reviewer_id":"c1"})
        r = client.post(f"{BASE}/{cid}/review/decide",
                        json={"reviewer_id":"c1","decision":"REJECT","note":"Docs unclear"})
        assert r.status_code == 200
        assert r.json()["case"]["status"] == "REJECTED"

    def test_cannot_review_without_docs(self):
        r = make_case("sess_fb_r4")
        cid = r.json()["case"]["case_id"]
        r2 = client.post(f"{BASE}/{cid}/review/start",
                         json={"reviewer_id":"c1"})
        assert r2.status_code == 422

    def test_invalid_decision_422(self):
        cid = self._setup_ready_case("sess_fb_r5")
        client.post(f"{BASE}/{cid}/review/start", json={"reviewer_id":"c1"})
        r = client.post(f"{BASE}/{cid}/review/decide",
                        json={"reviewer_id":"c1","decision":"MAYBE"})
        assert r.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 4. Get & Session Lookup (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestGetCase:
    def test_get_by_case_id(self):
        r = make_case("sess_fb_g1")
        cid = r.json()["case"]["case_id"]
        r2 = client.get(f"{BASE}/{cid}")
        assert r2.status_code == 200
        assert r2.json()["case"]["case_id"] == cid

    def test_get_by_session_id(self):
        make_case("sess_fb_g2")
        r = client.get(f"{BASE}/session/sess_fb_g2")
        assert r.status_code == 200
        assert r.json()["case"]["session_id"] == "sess_fb_g2"

    def test_get_nonexistent_404(self):
        assert client.get(f"{BASE}/FKYC-NOTEXIST").status_code == 404

# ══════════════════════════════════════════════════════════════════════════
# 5. Stats & Document Types (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestStatsAndTypes:
    def test_stats_200(self):
        assert client.get(f"{BASE}/stats").status_code == 200

    def test_stats_has_all_statuses(self):
        r = client.get(f"{BASE}/stats")
        d = r.json()["stats"]
        for s in ["INITIATED","DOCS_PENDING","DOCS_SUBMITTED","UNDER_REVIEW","APPROVED","REJECTED"]:
            assert s in d, f"Missing status: {s}"

    def test_document_types_200(self):
        r = client.get(f"{BASE}/document-types")
        assert r.status_code == 200
        assert "NID_FRONT" in r.json()["document_types"]
        assert "NID_API_UNAVAILABLE" in r.json()["trigger_codes"]
