"""
M58 — KYC Workflow Engine Tests
BFIU Circular No. 29 — Full workflow compliance
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.services.kyc_workflow_engine import (
    clear_sessions,
    create_kyc_session, get_kyc_session, get_session_summary,
    submit_data_capture, submit_nid_verification, submit_biometric,
    submit_screening, submit_risk_assessment, make_decision,
    SIMPLIFIED_STEPS, REGULAR_STEPS,
)

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────
_DEMO_NIDS = ["1234567890123", "9876543210987", "1111111111111"]
_nid_idx = 0

def _unique_nid():
    """Cycle through known demo NIDs."""
    global _nid_idx
    nid = _DEMO_NIDS[_nid_idx % len(_DEMO_NIDS)]
    _nid_idx += 1
    return nid



@pytest.fixture(autouse=True)
def patch_gate(monkeypatch):
    """Bypass BFIU Redis session limits in unit tests."""
    monkeypatch.setattr(
        "app.services.session_limiter.gate_attempt",
        lambda nid, sid: {"allowed": True, "reason": "TEST_BYPASS"},
    )
    monkeypatch.setattr(
        "app.services.session_limiter.increment_attempt_count",
        lambda sid: None,
    )
    monkeypatch.setattr(
        "app.services.session_limiter.increment_session_count",
        lambda nid_hash: None,
    )
    monkeypatch.setattr(
        "app.services.session_limiter.check_attempt_limit",
        lambda sid: {"current_count": 1, "max_count": 10, "allowed": True},
    )

# ── Auth helper ───────────────────────────────────────────────────────────
def get_token():
    r = client.post("/api/v1/auth/token", json={
        "email": "agent@demo.ekyc", "password": "DemoAgent@2026"
    })
    return r.json().get("access_token", "")

# ── Step definitions ──────────────────────────────────────────────────────
class TestStepDefinitions:
    def test_simplified_steps(self):
        assert SIMPLIFIED_STEPS == [
            "data_capture", "nid_verification", "biometric", "screening", "decision"
        ]

    def test_regular_steps(self):
        assert REGULAR_STEPS == [
            "data_capture", "nid_verification", "biometric",
            "screening", "risk_assessment", "decision"
        ]

    def test_regular_has_risk_step(self):
        assert "risk_assessment" in REGULAR_STEPS

    def test_simplified_no_risk_step(self):
        assert "risk_assessment" not in SIMPLIFIED_STEPS


# ── Session creation ──────────────────────────────────────────────────────
class TestSessionCreation:
    def test_create_simplified_session(self):
        s = create_kyc_session(kyc_type="SIMPLIFIED")
        assert s["kyc_type"] == "SIMPLIFIED"
        assert s["current_step"] == "data_capture"
        assert s["status"] == "IN_PROGRESS"

    def test_create_regular_session(self):
        s = create_kyc_session(kyc_type="REGULAR")
        assert s["kyc_type"] == "REGULAR"
        assert s["steps"] == REGULAR_STEPS

    def test_session_has_id(self):
        s = create_kyc_session()
        assert "session_id" in s
        assert len(s["session_id"]) == 36

    def test_session_has_audit_trail(self):
        s = create_kyc_session()
        assert len(s["audit_trail"]) >= 1

    def test_session_bfiu_ref(self):
        s = create_kyc_session()
        assert "BFIU" in s["bfiu_ref"]

    def test_get_session(self):
        s = create_kyc_session()
        fetched = get_kyc_session(s["session_id"])
        assert fetched["session_id"] == s["session_id"]

    def test_get_nonexistent_session(self):
        assert get_kyc_session("nonexistent-id") is None

    def test_invalid_kyc_type_defaults_simplified(self):
        s = create_kyc_session(kyc_type="INVALID")
        assert s["kyc_type"] == "SIMPLIFIED"


# ── Data capture ──────────────────────────────────────────────────────────
class TestDataCapture:
    def setup_method(self, monkeypatch=None):
        clear_sessions()

    def _session(self, kyc_type="SIMPLIFIED"):
        return create_kyc_session(kyc_type=kyc_type)

    def test_simplified_data_capture_ok(self):
        s = self._session()
        r = submit_data_capture(s["session_id"], {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
        })
        assert r["step_completed"] == "data_capture"
        assert r["next_step"] == "nid_verification"

    def test_regular_requires_income_and_source(self):
        s = self._session("REGULAR")
        r = submit_data_capture(s["session_id"], {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
            # missing monthly_income, source_of_funds, profession
        })
        assert r.get("error") is True
        assert "monthly_income" in r["message"] or "source_of_funds" in r["message"]

    def test_missing_name_fails(self):
        s = self._session()
        r = submit_data_capture(s["session_id"], {
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
        })
        assert r.get("error") is True

    def test_data_stored_in_session(self):
        s = self._session()
        submit_data_capture(s["session_id"], {
            "full_name_en": "FATEMA BEGUM",
            "date_of_birth": "1985-06-20",
            "mobile_phone": "01700000002",
            "present_address": "456 Chittagong",
        })
        updated = get_kyc_session(s["session_id"])
        assert updated["data"]["full_name_en"] == "FATEMA BEGUM"


# ── NID verification ──────────────────────────────────────────────────────
class TestNIDVerification:
    def setup_method(self, monkeypatch=None):
        clear_sessions()
  # NIDs: 1234567890123, 0000000000000
    def _ready_session(self, kyc_type="SIMPLIFIED"):
        s = create_kyc_session(kyc_type=kyc_type)
        submit_data_capture(s["session_id"], {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
        })
        return s

    def test_known_nid_verified(self):
        s = self._ready_session()
        r = submit_nid_verification(s["session_id"], _unique_nid())
        assert r["step_completed"] == "nid_verification"
        assert r["verified"] is True

    def test_unknown_nid_rejected(self):
        s = self._ready_session()
        r = submit_nid_verification(s["session_id"], "0000000000000")
        assert r.get("error") is True or get_kyc_session(s["session_id"])["status"] == "REJECTED"

    def test_nid_ec_source_demo(self):
        s = self._ready_session()
        r = submit_nid_verification(s["session_id"], "1234567890123")
        assert r["ec_source"] == "DEMO"

    def test_next_step_after_nid(self):
        s = self._ready_session()
        r = submit_nid_verification(s["session_id"], "1234567890123")
        assert r["next_step"] == "biometric"


# ── Biometric ─────────────────────────────────────────────────────────────
class TestBiometric:
    def setup_method(self, monkeypatch=None):
        clear_sessions()

    def _ready_session(self):
        s = create_kyc_session()
        submit_data_capture(s["session_id"], {
            "full_name_en": "FATEMA BEGUM",
            "date_of_birth": "1985-06-20",
            "mobile_phone": "01700000002",
            "present_address": "456 Dhaka",
        })
        submit_nid_verification(s["session_id"], _unique_nid())
        return s

    def test_biometric_pass(self):
        s = self._ready_session()
        r = submit_biometric(s["session_id"], {"passed": True, "confidence": 85.0})
        assert r["next_step"] == "screening"

    def test_biometric_fail_rejected(self):
        s = self._ready_session()
        r = submit_biometric(s["session_id"], {"passed": False, "confidence": 20.0, "failed_session_count": 1})
        assert r["status"] == "REJECTED"

    def test_biometric_fail_offers_fallback_after_3(self):
        s = self._ready_session()
        r = submit_biometric(s["session_id"], {"passed": False, "confidence": 20.0, "failed_session_count": 3})
        assert r["offer_fallback"] is True

    def test_biometric_fail_no_fallback_first_attempt(self):
        s = self._ready_session()
        r = submit_biometric(s["session_id"], {"passed": False, "confidence": 20.0, "failed_session_count": 1})
        assert r["offer_fallback"] is False


# ── Screening ─────────────────────────────────────────────────────────────
class TestScreening:
    def setup_method(self, monkeypatch=None):
        clear_sessions()

    def _ready_session(self, kyc_type="SIMPLIFIED"):
        s = create_kyc_session(kyc_type=kyc_type)
        submit_data_capture(s["session_id"], {
            "full_name_en": "KARIM UDDIN AHMED",
            "date_of_birth": "1975-03-10",
            "mobile_phone": "01700000003",
            "present_address": "789 Sylhet",
        })
        submit_nid_verification(s["session_id"], _unique_nid())
        submit_biometric(s["session_id"], {"passed": True, "confidence": 85.0})
        return s

    def test_screening_clear_advances(self):
        s = self._ready_session()
        r = submit_screening(s["session_id"], "RAHMAN HOSSAIN")
        assert r.get("error") is None
        assert r["step_completed"] == "screening"

    def test_simplified_next_step_is_decision(self):
        s = self._ready_session("SIMPLIFIED")
        r = submit_screening(s["session_id"], "RAHMAN HOSSAIN")
        assert r["next_step"] == "decision"

    def test_regular_next_step_is_risk(self):
        s = create_kyc_session(kyc_type="REGULAR")
        submit_data_capture(s["session_id"], {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
            "monthly_income": 50000,
            "source_of_funds": "Salary",
            "profession": "Engineer",
        })
        submit_nid_verification(s["session_id"], "1234567890123")
        submit_biometric(s["session_id"], {"passed": True, "confidence": 85.0})
        r = submit_screening(s["session_id"], "RAHMAN HOSSAIN")
        assert r["next_step"] == "risk_assessment"


# ── Decision logic ────────────────────────────────────────────────────────
class TestDecision:
    def setup_method(self, monkeypatch=None):
        clear_sessions()

    def _simplified_ready_for_decision(self):
        s = create_kyc_session(kyc_type="SIMPLIFIED")
        submit_data_capture(s["session_id"], {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
        })
        submit_nid_verification(s["session_id"], _unique_nid())
        submit_biometric(s["session_id"], {"passed": True, "confidence": 85.0})
        submit_screening(s["session_id"], "RAHMAN HOSSAIN")
        return s

    def test_simplified_low_risk_approved(self):
        s = self._simplified_ready_for_decision()
        r = make_decision(s["session_id"])
        assert r["decision"] == "APPROVED"

    def test_decision_has_bfiu_ref(self):
        s = self._simplified_ready_for_decision()
        r = make_decision(s["session_id"])
        assert "BFIU" in r["bfiu_ref"]

    def test_decision_has_kyc_type(self):
        s = self._simplified_ready_for_decision()
        r = make_decision(s["session_id"])
        assert r["kyc_type"] == "SIMPLIFIED"

    def test_session_status_approved(self):
        s = self._simplified_ready_for_decision()
        make_decision(s["session_id"])
        updated = get_kyc_session(s["session_id"])
        assert updated["status"] == "APPROVED"

    def test_regular_high_risk_edd(self):
        s = create_kyc_session(kyc_type="REGULAR")
        submit_data_capture(s["session_id"], {
            "full_name_en": "KARIM UDDIN",
            "date_of_birth": "1975-03-10",
            "mobile_phone": "01700000003",
            "present_address": "789 Sylhet",
            "monthly_income": 5000000,
            "source_of_funds": "Business",
            "profession": "Businessman",
        })
        submit_nid_verification(s["session_id"], "1111111111111")
        submit_biometric(s["session_id"], {"passed": True, "confidence": 85.0})
        submit_screening(s["session_id"], "KARIM UDDIN")
        submit_risk_assessment(s["session_id"], {
            "onboarding_channel": "WALK_IN",
            "residency": "RESIDENT",
            "pep_ip_status": "PEP",
            "product_type": "UNIVERSAL_LIFE",
            "institution_type": "INSURANCE",
            "business_type": "MONEY_EXCHANGE",
            "monthly_income": 5000000,
        })
        r = make_decision(s["session_id"])
        assert r["decision"] == "EDD_REQUIRED"
        assert r["edd_required"] is True


# ── Full flow E2E ─────────────────────────────────────────────────────────
class TestFullFlow:
    def setup_method(self, monkeypatch=None):
        clear_sessions()

    def test_simplified_full_flow(self):
        s = create_kyc_session(kyc_type="SIMPLIFIED")
        sid = s["session_id"]
        submit_data_capture(sid, {
            "full_name_en": "FATEMA BEGUM",
            "date_of_birth": "1985-06-20",
            "mobile_phone": "01700000002",
            "present_address": "456 Dhanmondi",
        })
        submit_nid_verification(sid, "9876543210987")
        submit_biometric(sid, {"passed": True, "confidence": 78.0})
        submit_screening(sid, "FATEMA BEGUM")
        r = make_decision(sid)
        assert r["decision"] == "APPROVED"
        summary = get_session_summary(sid)
        assert len(summary["completed_steps"]) == 5

    def test_regular_full_flow(self):
        s = create_kyc_session(kyc_type="REGULAR")
        sid = s["session_id"]
        submit_data_capture(sid, {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Agrabad",
            "monthly_income": 80000,
            "source_of_funds": "Salary",
            "profession": "Engineer",
        })
        submit_nid_verification(sid, "1234567890123")
        submit_biometric(sid, {"passed": True, "confidence": 90.0})
        submit_screening(sid, "RAHMAN HOSSAIN")
        submit_risk_assessment(sid, {
            "onboarding_channel": "DIGITAL_DIRECT",
            "residency": "RESIDENT",
            "pep_ip_status": "NONE",
            "product_type": "ORDINARY_LIFE",
            "institution_type": "INSURANCE",
            "business_type": "TECHNOLOGY",
            "monthly_income": 80000,
        })
        r = make_decision(sid)
        assert r["decision"] in ("APPROVED", "CONDITIONAL", "EDD_REQUIRED")
        summary = get_session_summary(sid)
        assert len(summary["completed_steps"]) == 6

    def test_audit_trail_populated(self):
        s = create_kyc_session(kyc_type="SIMPLIFIED")
        sid = s["session_id"]
        submit_data_capture(sid, {
            "full_name_en": "RAHMAN HOSSAIN",
            "date_of_birth": "1990-01-15",
            "mobile_phone": "01700000001",
            "present_address": "123 Dhaka",
        })
        session = get_kyc_session(sid)
        assert len(session["audit_trail"]) >= 2


# ── API endpoints ─────────────────────────────────────────────────────────
class TestKYCWorkflowAPI:
    def setup_method(self):
        self.token = get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_start_session_api(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED", "agent_id": "agent-01"},
            headers=self.headers)
        assert r.status_code == 201
        assert "session_id" in r.json()

    def test_invalid_kyc_type_api(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "INVALID"},
            headers=self.headers)
        assert r.status_code == 422

    def test_get_session_api(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED"},
            headers=self.headers)
        sid = r.json()["session_id"]
        r2 = client.get(f"/api/v1/kyc-workflow/{sid}", headers=self.headers)
        assert r2.status_code == 200
        assert r2.json()["session_id"] == sid

    def test_session_not_found_404(self):
        r = client.get("/api/v1/kyc-workflow/nonexistent-id", headers=self.headers)
        assert r.status_code == 404

    def test_data_capture_api(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED"},
            headers=self.headers)
        sid = r.json()["session_id"]
        r2 = client.post(f"/api/v1/kyc-workflow/{sid}/data-capture",
            json={
                "full_name_en": "RAHMAN HOSSAIN",
                "date_of_birth": "1990-01-15",
                "mobile_phone": "01700000001",
                "present_address": "123 Dhaka",
            },
            headers=self.headers)
        assert r2.status_code == 200
        assert r2.json()["next_step"] == "nid_verification"

    def test_nid_verify_api_known_nid(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED"},
            headers=self.headers)
        sid = r.json()["session_id"]
        client.post(f"/api/v1/kyc-workflow/{sid}/data-capture",
            json={"full_name_en": "RAHMAN HOSSAIN", "date_of_birth": "1990-01-15",
                  "mobile_phone": "01700000001", "present_address": "123 Dhaka"},
            headers=self.headers)
        r2 = client.post(f"/api/v1/kyc-workflow/{sid}/nid-verify",
            json={"nid_number": "1234567890123"},
            headers=self.headers)
        assert r2.status_code == 200
        assert r2.json()["next_step"] == "biometric"

    def test_full_simplified_flow_api(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED"},
            headers=self.headers)
        sid = r.json()["session_id"]

        client.post(f"/api/v1/kyc-workflow/{sid}/data-capture",
            json={"full_name_en": "FATEMA BEGUM", "date_of_birth": "1985-06-20",
                  "mobile_phone": "01700000002", "present_address": "456 Dhaka"},
            headers=self.headers)

        client.post(f"/api/v1/kyc-workflow/{sid}/nid-verify",
            json={"nid_number": "9876543210987"},
            headers=self.headers)

        client.post(f"/api/v1/kyc-workflow/{sid}/biometric",
            json={"passed": True, "confidence": 82.0},
            headers=self.headers)

        client.post(f"/api/v1/kyc-workflow/{sid}/screening",
            json={}, headers=self.headers)

        r_dec = client.post(f"/api/v1/kyc-workflow/{sid}/decision",
            headers=self.headers)
        assert r_dec.status_code == 200
        assert r_dec.json()["decision"] == "APPROVED"

    def test_summary_api(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED"},
            headers=self.headers)
        sid = r.json()["session_id"]
        r2 = client.get(f"/api/v1/kyc-workflow/{sid}/summary", headers=self.headers)
        assert r2.status_code == 200
        assert "completed_steps" in r2.json()

    def test_unauthenticated_rejected(self):
        r = client.post("/api/v1/kyc-workflow/session",
            json={"kyc_type": "SIMPLIFIED"})
        assert r.status_code == 403
