"""
M4 - Fingerprint Onboarding Wizard Tests
Tests: 5-step wizard, state machine, fallback trigger, signature rules, notification
Replaces old urllib-based test_fingerprint.py with proper TestClient tests
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Wizard service unit tests
# ---------------------------------------------------------------------------
class TestWizardSession:
    def setup_method(self):
        from app.services.onboarding_wizard import (
            create_wizard_session, get_wizard_session,
            reset_wizard_sessions, STEPS,
        )
        self.create  = create_wizard_session
        self.get     = get_wizard_session
        self.reset   = reset_wizard_sessions
        self.STEPS   = STEPS
        self.reset()

    def test_session_created_at_step_1(self):
        s = self.create("1234567890123", "agent-001")
        assert s["current_step"] == 1
        assert s["current_step_name"] == "NID_VERIFICATION"

    def test_session_has_uuid(self):
        s = self.create("1234567890123", "agent-001")
        assert len(s["session_id"]) == 36

    def test_session_status_in_progress(self):
        s = self.create("1234567890123", "agent-001")
        assert s["status"] == "IN_PROGRESS"

    def test_session_retrieved_by_id(self):
        s  = self.create("1234567890123", "agent-001")
        s2 = self.get(s["session_id"])
        assert s2["session_id"] == s["session_id"]

    def test_unknown_session_returns_none(self):
        assert self.get("nonexistent-id") is None

    def test_total_steps_is_5(self):
        assert len(self.STEPS) == 7  # BFIU Circular No. 29 7-step flow

    def test_step_names_correct(self):
        assert self.STEPS[1] == "NID_VERIFICATION"
        assert self.STEPS[2] == "BIOMETRIC"
        assert self.STEPS[3] == "PERSONAL_INFO"
        assert self.STEPS[4] == "PHOTOGRAPH"
        assert self.STEPS[5] == "SIGNATURE"
        assert self.STEPS[6] == "SCREENING"
        assert self.STEPS[7] == "NOTIFICATION"


# ---------------------------------------------------------------------------
# Step processing tests
# ---------------------------------------------------------------------------
class TestStepProcessing:
    def setup_method(self):
        from app.services.onboarding_wizard import (
            create_wizard_session, process_step,
            reset_wizard_sessions,
        )
        self.create  = create_wizard_session
        self.process = process_step
        self.reset   = reset_wizard_sessions
        self.reset()

    def _new_session(self):
        return self.create("1234567890123", "agent-001")

    def test_step1_advances_to_step2(self):
        s = self._new_session()
        r = self.process(s["session_id"], {
            "nid_number": "1234567890123",
            "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        assert r["success"] is True
        assert r["next_step"] == "BIOMETRIC"

    def test_step1_missing_nid_fails(self):
        s = self._new_session()
        r = self.process(s["session_id"], {
            "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        assert r["success"] is False

    def test_step1_missing_fingerprint_fails(self):
        s = self._new_session()
        r = self.process(s["session_id"], {
            "nid_number": "1234567890123",
            "dob": "1990-01-15",
        })
        assert r["success"] is False

    def test_step2_advances_to_step3(self):
        s = self._new_session()
        self.process(s["session_id"], {
            "nid_number": "1234567890123",
            "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        r = self.process(s["session_id"], {
            "biometric_passed": True,
            "biometric_mode": "FINGERPRINT",
        })
        assert r["success"] is True
        assert r["next_step"] == "PERSONAL_INFO"

    def test_step3_advances_to_step4(self):
        s = self._new_session()
        self.process(s["session_id"], {
            "nid_number": "1234567890123", "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        self.process(s["session_id"], {
            "biometric_passed": True, "biometric_mode": "FINGERPRINT",
        })
        r = self.process(s["session_id"], {
            "full_name": "RAHMAN HOSSAIN", "mobile": "+8801712345678",
        })
        assert r["success"] is True
        assert r["next_step"] == "PHOTOGRAPH"

    def test_step4_pin_allowed_for_low_risk(self):
        s = self._new_session()
        self.process(s["session_id"], {
            "nid_number": "1234567890123", "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        self.process(s["session_id"], {
            "biometric_passed": True, "biometric_mode": "FINGERPRINT",
        })
        self.process(s["session_id"], {
            "full_name": "RAHMAN HOSSAIN", "mobile": "+8801712345678",
        })
        self.process(s["session_id"], {"photo_b64": "photodummyb64"})
        r = self.process(s["session_id"], {
            "signature_type": "PIN", "risk_grade": "LOW"
        })
        assert r["success"] is True

    def test_step4_pin_rejected_for_high_risk(self):
        s = self._new_session()
        self.process(s["session_id"], {
            "nid_number": "1234567890123", "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        self.process(s["session_id"], {
            "biometric_passed": True, "biometric_mode": "FINGERPRINT",
        })
        self.process(s["session_id"], {
            "full_name": "RAHMAN HOSSAIN", "mobile": "+8801712345678",
        })
        self.process(s["session_id"], {"photo_b64": "photodummyb64"})
        r = self.process(s["session_id"], {
            "signature_type": "PIN", "risk_grade": "HIGH"
        })
        assert r["success"] is False

    def test_full_7_step_flow_completes(self):
        s = self._new_session()
        sid = s["session_id"]
        self.process(sid, {
            "nid_number": "1234567890123", "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        self.process(sid, {
            "biometric_passed": True, "biometric_mode": "FINGERPRINT",
        })
        self.process(sid, {
            "full_name": "RAHMAN HOSSAIN", "mobile": "+8801712345678",
        })
        self.process(sid, {"photo_b64": "photodummyb64"})
        self.process(sid, {"signature_type": "WET", "risk_grade": "LOW"})
        self.process(sid, {"screening_result": "CLEAR"})
        r = self.process(sid, {
            "mobile": "+8801712345678", "email": "test@demo.com"
        })
        assert r["success"] is True
        assert r["status"] == "COMPLETED"

    def test_completed_session_rejects_further_steps(self):
        s = self._new_session()
        sid = s["session_id"]
        self.process(sid, {
            "nid_number": "1234567890123", "dob": "1990-01-15",
            "fingerprint_b64": "dummyb64",
        })
        self.process(sid, {
            "biometric_passed": True, "biometric_mode": "FINGERPRINT",
        })
        self.process(sid, {
            "full_name": "RAHMAN HOSSAIN", "mobile": "+8801712345678",
        })
        self.process(sid, {"photo_b64": "photodummyb64"})
        self.process(sid, {"signature_type": "WET", "risk_grade": "LOW"})
        self.process(sid, {"screening_result": "CLEAR"})
        self.process(sid, {"mobile": "+8801712345678", "email": "test@demo.com"})
        r = self.process(sid, {"mobile": "+8801712345678"})
        assert r["success"] is False


# ---------------------------------------------------------------------------
# Fallback trigger tests
# ---------------------------------------------------------------------------
class TestFallbackTrigger:
    def setup_method(self):
        from app.services.onboarding_wizard import (
            create_wizard_session, record_failed_session,
            reset_wizard_sessions, FALLBACK_SESSION_THRESHOLD,
        )
        self.create    = create_wizard_session
        self.fail      = record_failed_session
        self.reset     = reset_wizard_sessions
        self.THRESHOLD = FALLBACK_SESSION_THRESHOLD
        self.reset()

    def test_fallback_threshold_is_3(self):
        assert self.THRESHOLD == 3

    def test_first_failure_no_fallback(self):
        s = self.create("1234567890123", "agent-001")
        r = self.fail(s["session_id"])
        assert r["fallback_required"] is False
        assert r["failed_sessions"] == 1

    def test_second_failure_no_fallback(self):
        s = self.create("1234567890123", "agent-001")
        self.fail(s["session_id"])
        r = self.fail(s["session_id"])
        assert r["fallback_required"] is False
        assert r["failed_sessions"] == 2

    def test_third_failure_triggers_fallback(self):
        s = self.create("1234567890123", "agent-001")
        self.fail(s["session_id"])
        self.fail(s["session_id"])
        r = self.fail(s["session_id"])
        assert r["fallback_required"] is True
        assert r["fallback_offered"] is True

    def test_fallback_message_contains_face_matching(self):
        s = self.create("1234567890123", "agent-001")
        self.fail(s["session_id"])
        self.fail(s["session_id"])
        r = self.fail(s["session_id"])
        assert "face" in r["message"].lower()

    def test_fallback_bfiu_ref(self):
        s = self.create("1234567890123", "agent-001")
        r = self.fail(s["session_id"])
        assert "3.2" in r["bfiu_ref"]


# ---------------------------------------------------------------------------
# Notification tests
# ---------------------------------------------------------------------------
class TestNotification:
    def setup_method(self):
        from app.services.onboarding_wizard import (
            create_wizard_session, process_step,
            generate_notification, reset_wizard_sessions,
        )
        self.create   = create_wizard_session
        self.process  = process_step
        self.notify   = generate_notification
        self.reset    = reset_wizard_sessions
        self.reset()

    def test_notification_has_id(self):
        s = self.create("1234567890123", "agent-001")
        n = self.notify(s)
        assert "notification_id" in n
        assert len(n["notification_id"]) == 36

    def test_notification_type_account_opening(self):
        s = self.create("1234567890123", "agent-001")
        n = self.notify(s)
        assert n["type"] == "ACCOUNT_OPENING"

    def test_notification_status_dispatched(self):
        s = self.create("1234567890123", "agent-001")
        n = self.notify(s)
        assert n["status"] == "DISPATCHED"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
class TestOnboardingAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        self.client.post("/api/v1/auth/register", json={
            "email": "maker_ob@demo.com",
            "phone": "+8801712345678",
            "full_name": "Onboarding Maker",
            "role": "MAKER",
            "password": "maker1234",
        })
        r = self.client.post("/api/v1/auth/token", json={
            "email": "maker_ob@demo.com",
            "password": "maker1234",
        })
        self.token   = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        from app.services.onboarding_wizard import reset_wizard_sessions
        reset_wizard_sessions()

    def test_start_session(self):
        r = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "1234567890123",
            "agent_id":   "agent-001",
            "channel":    "AGENCY",
        }, headers=self.headers)
        assert r.status_code == 201
        data = r.json()
        assert data["success"] is True
        assert data["current_step"] == 1
        assert "session_id" in data

    def test_start_invalid_nid_fails(self):
        r = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "123",
            "agent_id":   "agent-001",
        }, headers=self.headers)
        assert r.status_code == 422

    def test_submit_step1(self):
        start = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "1234567890123",
            "agent_id":   "agent-001",
        }, headers=self.headers)
        sid = start.json()["session_id"]
        r = self.client.post("/api/v1/onboarding/step", json={
            "session_id": sid,
            "step_data":  {
                "nid_number": "1234567890123",
                "dob": "1990-01-15",
                "fingerprint_b64": "dummyb64",
            },
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["next_step"] == "BIOMETRIC"

    def test_fail_session_endpoint(self):
        start = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "1234567890123",
            "agent_id":   "agent-001",
        }, headers=self.headers)
        sid = start.json()["session_id"]
        r = self.client.post("/api/v1/onboarding/fail", json={
            "session_id": sid, "reason": "fingerprint not matched",
        }, headers=self.headers)
        assert r.status_code == 200
        assert "failed_sessions" in r.json()

    def test_fallback_triggered_after_3_fails(self):
        start = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "1234567890123",
            "agent_id":   "agent-001",
        }, headers=self.headers)
        sid = start.json()["session_id"]
        for _ in range(3):
            self.client.post("/api/v1/onboarding/fail", json={
                "session_id": sid,
            }, headers=self.headers)
        r = self.client.post("/api/v1/onboarding/fail", json={
            "session_id": sid,
        }, headers=self.headers)
        assert r.json()["fallback_required"] is True

    def test_get_session(self):
        start = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "1234567890123",
            "agent_id":   "agent-001",
        }, headers=self.headers)
        sid = start.json()["session_id"]
        r = self.client.get(
            f"/api/v1/onboarding/session/{sid}",
            headers=self.headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == sid
        assert "nid_number" not in data

    def test_get_steps(self):
        r = self.client.get("/api/v1/onboarding/steps", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_steps"] == 7
        assert data["fallback_threshold"] == 3

    def test_unauthenticated_start_fails(self):
        r = self.client.post("/api/v1/onboarding/start", json={
            "nid_number": "1234567890123",
            "agent_id":   "agent-001",
        })
        assert r.status_code == 403
