"""
test_compliance.py - M14 Compliance Dashboard API
Tests: Posture, KYC Queues, EDD Cases, Screening Hits,
       Failed Onboarding, Export, Metrics
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE = "/api/v1/compliance"

# ══════════════════════════════════════════════════════════════════════════
# 1. Posture (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestPosture:
    def test_posture_200(self):
        r = client.get(f"{BASE}/posture")
        assert r.status_code == 200

    def test_posture_has_all_sections(self):
        d = client.get(f"{BASE}/posture").json()
        for key in ["kyc_reviews","edd","screening","failed_onboarding","overall_status","bfiu_ref"]:
            assert key in d, f"Missing: {key}"

    def test_posture_kyc_reviews_breakdown(self):
        d = client.get(f"{BASE}/posture").json()
        kr = d["kyc_reviews"]
        assert "high_risk" in kr and "medium_risk" in kr and "low_risk" in kr
        assert kr["total_pending"] == kr["high_risk"] + kr["medium_risk"] + kr["low_risk"]

    def test_posture_overall_status_valid(self):
        d = client.get(f"{BASE}/posture").json()
        assert d["overall_status"] in ("ACTION_REQUIRED", "REVIEW_PENDING")

    def test_posture_bfiu_ref_present(self):
        d = client.get(f"{BASE}/posture").json()
        assert "BFIU" in d["bfiu_ref"]

# ══════════════════════════════════════════════════════════════════════════
# 2. KYC Queues (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestKYCQueues:
    def test_queues_200(self):
        assert client.get(f"{BASE}/kyc-queues").status_code == 200

    def test_queues_has_summary(self):
        d = client.get(f"{BASE}/kyc-queues").json()
        assert "queues" in d and "summary" in d and "total" in d

    def test_queues_filter_high(self):
        d = client.get(f"{BASE}/kyc-queues?grade=HIGH").json()
        assert all(q["risk_grade"] == "HIGH" for q in d["queues"])

    def test_queues_filter_medium(self):
        d = client.get(f"{BASE}/kyc-queues?grade=MEDIUM").json()
        assert all(q["risk_grade"] == "MEDIUM" for q in d["queues"])

    def test_queues_filter_low(self):
        d = client.get(f"{BASE}/kyc-queues?grade=LOW").json()
        assert all(q["risk_grade"] == "LOW" for q in d["queues"])

    def test_queues_review_intervals(self):
        d = client.get(f"{BASE}/kyc-queues").json()
        ri = d["review_intervals_years"]
        assert ri["HIGH"] == 1 and ri["MEDIUM"] == 2 and ri["LOW"] == 5

# ══════════════════════════════════════════════════════════════════════════
# 3. EDD Cases (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestEDDCases:
    def test_edd_200(self):
        assert client.get(f"{BASE}/edd-cases").status_code == 200

    def test_edd_has_cases(self):
        d = client.get(f"{BASE}/edd-cases").json()
        assert "cases" in d and d["total"] > 0

    def test_edd_filter_open(self):
        d = client.get(f"{BASE}/edd-cases?status=OPEN").json()
        assert all(c["status"] == "OPEN" for c in d["cases"])

    def test_edd_filter_escalated(self):
        d = client.get(f"{BASE}/edd-cases?status=ESCALATED").json()
        assert all(c["status"] == "ESCALATED" for c in d["cases"])

    def test_edd_case_has_required_fields(self):
        d = client.get(f"{BASE}/edd-cases").json()
        c = d["cases"][0]
        for f in ["id","customer_name","risk_score","trigger","status","assigned_to"]:
            assert f in c, f"Missing field: {f}"

# ══════════════════════════════════════════════════════════════════════════
# 4. Screening Hits (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestScreeningHits:
    def test_screening_200(self):
        assert client.get(f"{BASE}/screening-hits").status_code == 200

    def test_screening_has_hits(self):
        d = client.get(f"{BASE}/screening-hits").json()
        assert "hits" in d and d["total"] > 0

    def test_screening_filter_blocked(self):
        d = client.get(f"{BASE}/screening-hits?verdict=BLOCKED").json()
        assert all(h["verdict"] == "BLOCKED" for h in d["hits"])

    def test_screening_filter_review(self):
        d = client.get(f"{BASE}/screening-hits?verdict=REVIEW").json()
        assert all(h["verdict"] == "REVIEW" for h in d["hits"])

    def test_screening_filter_unscr(self):
        d = client.get(f"{BASE}/screening-hits?check_type=UNSCR").json()
        assert all(h["check_type"] == "UNSCR" for h in d["hits"])

    def test_screening_hit_has_required_fields(self):
        d = client.get(f"{BASE}/screening-hits").json()
        h = d["hits"][0]
        for f in ["id","customer_name","check_type","match_score","verdict","matched_list"]:
            assert f in h, f"Missing field: {f}"

# ══════════════════════════════════════════════════════════════════════════
# 5. Failed Onboarding (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestFailedOnboarding:
    def test_failed_200(self):
        assert client.get(f"{BASE}/failed-onboarding").status_code == 200

    def test_failed_has_entries(self):
        d = client.get(f"{BASE}/failed-onboarding").json()
        assert "failures" in d and d["total"] > 0

    def test_failed_has_by_step(self):
        d = client.get(f"{BASE}/failed-onboarding").json()
        assert "by_step" in d and len(d["by_step"]) > 0

    def test_failed_filter_by_step(self):
        d = client.get(f"{BASE}/failed-onboarding?step=NID_VERIFICATION").json()
        assert all(f["step"] == "NID_VERIFICATION" for f in d["failures"])

    def test_failed_entry_has_required_fields(self):
        d = client.get(f"{BASE}/failed-onboarding").json()
        f = d["failures"][0]
        for field in ["id","step","reason","attempts","timestamp","agent"]:
            assert field in f, f"Missing field: {field}"

# ══════════════════════════════════════════════════════════════════════════
# 6. Export (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestExport:
    def test_export_json_200(self):
        assert client.get(f"{BASE}/export?fmt=json").status_code == 200

    def test_export_csv_200(self):
        assert client.get(f"{BASE}/export?fmt=csv").status_code == 200

    def test_export_json_has_data(self):
        d = client.get(f"{BASE}/export?fmt=json").json()
        assert d["format"] == "json"
        assert isinstance(d["data"], dict)
        assert "edd_cases" in d["data"]
        assert "screening_hits_detail" in d["data"]

    def test_export_csv_has_header(self):
        d = client.get(f"{BASE}/export?fmt=csv").json()
        assert d["format"] == "csv"
        assert "section,id,customer_name" in d["data"]

    def test_export_invalid_format_422(self):
        r = client.get(f"{BASE}/export?fmt=xml")
        assert r.status_code == 422

# ══════════════════════════════════════════════════════════════════════════
# 7. Metrics (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestMetrics:
    def test_metrics_200(self):
        assert client.get(f"{BASE}/metrics").status_code == 200

    def test_metrics_30_days(self):
        d = client.get(f"{BASE}/metrics").json()
        assert len(d["days"]) == 30

    def test_metrics_day_has_fields(self):
        d = client.get(f"{BASE}/metrics").json()
        day = d["days"][0]
        for f in ["date","onboarding_ok","onboarding_fail","screening_hits","edd_triggered"]:
            assert f in day, f"Missing: {f}"

    def test_metrics_period_label(self):
        d = client.get(f"{BASE}/metrics").json()
        assert d["period"] == "last_30_days"
