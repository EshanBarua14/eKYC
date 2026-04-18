"""
test_notification.py - M17 SMS/Email Notification Service
Tests: success notification, failure notification, log, stats, templates
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/notify"

SUCCESS_PAYLOAD = {
    "session_id":       "sess_notif_01",
    "full_name":        "Md. Rahman Hossain",
    "mobile":           "01712345678",
    "email":            "rahman@example.com",
    "account_number":   "ACC-2026-001",
    "branch":           "Dhaka Main",
    "account_type":     "Savings",
    "service_number":   "SVC-001",
    "kyc_type":         "SIMPLIFIED",
    "risk_grade":       "LOW",
    "confidence":       87.5,
    "institution_name": "First Insurance Ltd.",
    "helpdesk_number":  "16100",
}

FAILURE_PAYLOAD = {
    "session_id":       "sess_notif_fail_01",
    "mobile":           "01712345678",
    "email":            "customer@example.com",
    "failed_step":      "FACE_MATCH",
    "reason":           "Face match confidence below threshold",
    "institution_name": "First Insurance Ltd.",
    "helpdesk_number":  "16100",
}

# ══════════════════════════════════════════════════════════════════════════
# 1. Success Notification (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestSuccessNotification:
    def test_success_returns_201(self):
        r = client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":"sess_s1"})
        assert r.status_code == 201

    def test_success_has_channels(self):
        r = client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":"sess_s2"})
        d = r.json()
        assert "channels" in d
        assert d["channels_notified"] >= 1

    def test_success_sms_channel_present(self):
        r = client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":"sess_s3"})
        channels = r.json()["channels"]
        assert any(c["channel"] == "SMS" for c in channels)

    def test_success_email_channel_present(self):
        r = client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":"sess_s4"})
        channels = r.json()["channels"]
        assert any(c["channel"] == "EMAIL" for c in channels)

    def test_success_bfiu_ref(self):
        r = client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":"sess_s5"})
        assert "BFIU" in r.json()["bfiu_ref"]

    def test_success_no_email_only_sms(self):
        payload = {**SUCCESS_PAYLOAD, "session_id":"sess_s6", "email": None}
        r = client.post(f"{BASE}/kyc-success", json=payload)
        assert r.status_code == 201
        assert r.json()["channels_notified"] == 1

# ══════════════════════════════════════════════════════════════════════════
# 2. Failure Notification (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestFailureNotification:
    def test_failure_returns_201(self):
        r = client.post(f"{BASE}/kyc-failure", json={**FAILURE_PAYLOAD,"session_id":"sess_f1"})
        assert r.status_code == 201

    def test_failure_has_channels(self):
        r = client.post(f"{BASE}/kyc-failure", json={**FAILURE_PAYLOAD,"session_id":"sess_f2"})
        assert r.json()["channels_notified"] >= 1

    def test_failure_type_correct(self):
        r = client.post(f"{BASE}/kyc-failure", json={**FAILURE_PAYLOAD,"session_id":"sess_f3"})
        assert r.json()["type"] == "KYC_FAILURE"

    def test_failure_bfiu_ref(self):
        r = client.post(f"{BASE}/kyc-failure", json={**FAILURE_PAYLOAD,"session_id":"sess_f4"})
        assert "BFIU" in r.json()["bfiu_ref"]

    def test_failure_no_email_only_sms(self):
        payload = {**FAILURE_PAYLOAD, "session_id":"sess_f5", "email": None}
        r = client.post(f"{BASE}/kyc-failure", json=payload)
        assert r.status_code == 201
        assert r.json()["channels_notified"] == 1

# ══════════════════════════════════════════════════════════════════════════
# 3. Delivery Log (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestDeliveryLog:
    def test_log_200(self):
        assert client.get(f"{BASE}/log").status_code == 200

    def test_log_has_entries_after_send(self):
        client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":"sess_log1"})
        r = client.get(f"{BASE}/log")
        assert r.json()["total"] >= 1

    def test_log_filter_by_session(self):
        sid = "sess_log_filter"
        client.post(f"{BASE}/kyc-success", json={**SUCCESS_PAYLOAD,"session_id":sid})
        r = client.get(f"{BASE}/log?session_id={sid}")
        assert all(l["session_id"]==sid for l in r.json()["logs"])

# ══════════════════════════════════════════════════════════════════════════
# 4. Stats (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestStats:
    def test_stats_200(self):
        assert client.get(f"{BASE}/stats").status_code == 200

    def test_stats_has_fields(self):
        r = client.get(f"{BASE}/stats")
        d = r.json()
        for k in ["total","sent","failed","sms_count","email_count","dev_mode"]:
            assert k in d, f"Missing: {k}"

    def test_stats_dev_mode_true(self):
        r = client.get(f"{BASE}/stats")
        assert r.json()["dev_mode"] is True

# ══════════════════════════════════════════════════════════════════════════
# 5. Templates (2 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestTemplates:
    def test_templates_200(self):
        assert client.get(f"{BASE}/templates").status_code == 200

    def test_templates_has_bfiu_required(self):
        r = client.get(f"{BASE}/templates")
        required = r.json()["bfiu_required"]
        assert "KYC_SUCCESS_SMS" in required
        assert "KYC_FAILURE_SMS" in required
