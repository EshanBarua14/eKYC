"""
test_outcome.py - M18 Onboarding Outcome State Machine
Tests: create, auto-route, checker decide, fallback, queue, transitions
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/outcome"

def make_outcome(session_id, verdict="MATCHED", risk_grade="LOW",
                 pep_flag=False, edd_required=False, screening_result="CLEAR",
                 confidence=87.5):
    return client.post(f"{BASE}/create", json={
        "session_id": session_id, "verdict": verdict,
        "confidence": confidence, "risk_grade": risk_grade,
        "pep_flag": pep_flag, "edd_required": edd_required,
        "screening_result": screening_result,
        "full_name": "Test User", "agent_id": "agent_01",
    })

# ══════════════════════════════════════════════════════════════════════════
# 1. Create (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestCreate:
    def test_create_201(self):
        r = make_outcome("sess_out_c1")
        assert r.status_code == 201

    def test_create_initial_state_pending(self):
        r = make_outcome("sess_out_c2")
        assert r.json()["outcome"]["state"] == "PENDING"

    def test_create_duplicate_409(self):
        make_outcome("sess_out_dup")
        r = make_outcome("sess_out_dup")
        assert r.status_code == 409

    def test_create_invalid_verdict_400(self):
        r = client.post(f"{BASE}/create", json={
            "session_id":"sess_bad_v","verdict":"INVALID","confidence":50.0})
        assert r.status_code == 400

# ══════════════════════════════════════════════════════════════════════════
# 2. Auto-route (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAutoRoute:
    def test_low_risk_matched_auto_approved(self):
        make_outcome("sess_ar_low", verdict="MATCHED", risk_grade="LOW")
        r = client.post(f"{BASE}/sess_ar_low/auto-route")
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "APPROVED"
        assert r.json()["auto_approved"] is True

    def test_high_risk_routes_to_pending_review(self):
        make_outcome("sess_ar_high", verdict="MATCHED", risk_grade="HIGH")
        r = client.post(f"{BASE}/sess_ar_high/auto-route")
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "PENDING_REVIEW"
        assert r.json()["auto_approved"] is False

    def test_medium_risk_routes_to_pending_review(self):
        make_outcome("sess_ar_med", verdict="MATCHED", risk_grade="MEDIUM")
        r = client.post(f"{BASE}/sess_ar_med/auto-route")
        assert r.json()["outcome"]["state"] == "PENDING_REVIEW"

    def test_pep_flag_routes_to_pending_review(self):
        make_outcome("sess_ar_pep", verdict="MATCHED", risk_grade="LOW", pep_flag=True)
        r = client.post(f"{BASE}/sess_ar_pep/auto-route")
        assert r.json()["outcome"]["state"] == "PENDING_REVIEW"

    def test_failed_verdict_routes_to_rejected(self):
        make_outcome("sess_ar_fail", verdict="FAILED", risk_grade="LOW", confidence=15.0)
        r = client.post(f"{BASE}/sess_ar_fail/auto-route")
        assert r.json()["outcome"]["state"] == "REJECTED"

    def test_sanctions_blocked_routes_to_rejected(self):
        make_outcome("sess_ar_blocked", verdict="MATCHED", risk_grade="LOW",
                     screening_result="BLOCKED")
        r = client.post(f"{BASE}/sess_ar_blocked/auto-route")
        assert r.json()["outcome"]["state"] == "REJECTED"

# ══════════════════════════════════════════════════════════════════════════
# 3. Checker Decision (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestCheckerDecision:
    def _make_pending_review(self, sid):
        make_outcome(sid, verdict="MATCHED", risk_grade="HIGH")
        client.post(f"{BASE}/{sid}/auto-route")

    def test_checker_approve(self):
        sid = "sess_chk_approve"
        self._make_pending_review(sid)
        r = client.post(f"{BASE}/{sid}/decide",
                        json={"checker_id":"checker_01","decision":"APPROVE","note":"Verified"})
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "APPROVED"

    def test_checker_reject(self):
        sid = "sess_chk_reject"
        self._make_pending_review(sid)
        r = client.post(f"{BASE}/{sid}/decide",
                        json={"checker_id":"checker_01","decision":"REJECT","note":"Suspicious"})
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "REJECTED"

    def test_checker_invalid_decision_422(self):
        sid = "sess_chk_bad"
        self._make_pending_review(sid)
        r = client.post(f"{BASE}/{sid}/decide",
                        json={"checker_id":"checker_01","decision":"MAYBE"})
        assert r.status_code == 422

    def test_checker_on_approved_fails(self):
        make_outcome("sess_chk_approved", verdict="MATCHED", risk_grade="LOW")
        client.post(f"{BASE}/sess_chk_approved/auto-route")
        r = client.post(f"{BASE}/sess_chk_approved/decide",
                        json={"checker_id":"c1","decision":"APPROVE"})
        assert r.status_code == 422

    def test_checker_id_recorded(self):
        sid = "sess_chk_id"
        self._make_pending_review(sid)
        client.post(f"{BASE}/{sid}/decide",
                    json={"checker_id":"checker_99","decision":"APPROVE"})
        r = client.get(f"{BASE}/{sid}")
        assert r.json()["outcome"]["checker_id"] == "checker_99"

# ══════════════════════════════════════════════════════════════════════════
# 4. Fallback (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestFallback:
    def test_fallback_sets_state(self):
        make_outcome("sess_fb_1", verdict="MATCHED", risk_grade="LOW")
        r = client.post(f"{BASE}/sess_fb_1/fallback",
                        json={"reason":"EC API unavailable"})
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "FALLBACK_KYC"
        assert r.json()["fallback_triggered"] is True

    def test_fallback_records_reason(self):
        make_outcome("sess_fb_2", verdict="MATCHED", risk_grade="LOW")
        client.post(f"{BASE}/sess_fb_2/fallback",
                    json={"reason":"Technical failure at EC server"})
        r = client.get(f"{BASE}/sess_fb_2")
        assert "Technical failure" in r.json()["outcome"]["fallback_reason"]

    def test_fallback_on_nonexistent_422(self):
        r = client.post(f"{BASE}/nonexistent_xyz/fallback",
                        json={"reason":"test"})
        assert r.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 5. Queue & Summary (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestQueue:
    def test_queue_summary_200(self):
        assert client.get(f"{BASE}/queue/summary").status_code == 200

    def test_queue_summary_has_states(self):
        r = client.get(f"{BASE}/queue/summary")
        d = r.json()["summary"]
        assert "PENDING_REVIEW" in d and "APPROVED" in d and "REJECTED" in d

    def test_pending_queue_200(self):
        assert client.get(f"{BASE}/queue/pending").status_code == 200

    def test_all_outcomes_filter_by_state(self):
        r = client.get(f"{BASE}/queue/all?state=APPROVED")
        assert r.status_code == 200
        assert all(o["state"]=="APPROVED" for o in r.json()["outcomes"])

# ══════════════════════════════════════════════════════════════════════════
# 6. History & Get (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestHistory:
    def test_get_outcome_200(self):
        make_outcome("sess_hist_1", verdict="MATCHED", risk_grade="LOW")
        r = client.get(f"{BASE}/sess_hist_1")
        assert r.status_code == 200

    def test_get_nonexistent_404(self):
        assert client.get(f"{BASE}/nonexistent_abc").status_code == 404

    def test_history_records_transitions(self):
        make_outcome("sess_hist_2", verdict="MATCHED", risk_grade="LOW")
        client.post(f"{BASE}/sess_hist_2/auto-route")
        r = client.get(f"{BASE}/sess_hist_2")
        history = r.json()["outcome"]["history"]
        assert len(history) >= 2
        states = [h["state"] for h in history]
        assert "PENDING" in states
        assert "APPROVED" in states
