"""
test_bfiu_report.py - M21 Monthly BFIU Report Generator
Tests: generate, sections, CSV, current month, list, validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/bfiu-report"

def generate_report(year=2026, month=4, institution_id="ALL"):
    return client.post(f"{BASE}/generate", json={
        "year": year, "month": month,
        "institution_id": institution_id,
        "submitted_by": "compliance_officer_01",
    })

# ══════════════════════════════════════════════════════════════════════════
# 1. Generate Report (6 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestGenerateReport:
    def test_generate_returns_201(self):
        r = generate_report()
        assert r.status_code == 201

    def test_report_has_id(self):
        r = generate_report()
        report = r.json()["report"]
        assert "report_id" in report
        assert report["report_id"].startswith("BFIU-")

    def test_report_has_all_sections(self):
        r = generate_report()
        report = r.json()["report"]
        for section in [
            "section_1_ekyc_openings",
            "section_2_risk_distribution",
            "section_3_failures",
            "section_4_screening",
            "section_5_cmi_bo",
            "section_6_notifications",
            "section_7_summary",
        ]:
            assert section in report, f"Missing section: {section}"

    def test_report_period_correct(self):
        r = generate_report(year=2026, month=3)
        report = r.json()["report"]
        assert report["period_year"]  == 2026
        assert report["period_month"] == 3
        assert "March 2026" in report["period_month_name"]

    def test_report_invalid_month_400(self):
        r = client.post(f"{BASE}/generate",
                        json={"year":2026,"month":13})
        assert r.status_code == 400

    def test_report_invalid_year_400(self):
        r = client.post(f"{BASE}/generate",
                        json={"year":2020,"month":1})
        assert r.status_code == 400

# ══════════════════════════════════════════════════════════════════════════
# 2. Section Content (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestReportSections:
    def _get_report(self):
        return generate_report().json()["report"]

    def test_section1_has_required_fields(self):
        s = self._get_report()["section_1_ekyc_openings"]
        for f in ["total_approved","simplified_ekyc","regular_ekyc",
                  "auto_approved","pending_checker_review","rejected"]:
            assert f in s, f"Missing: {f}"

    def test_section2_has_risk_fields(self):
        s = self._get_report()["section_2_risk_distribution"]
        for f in ["low_risk","medium_risk","high_risk","edd_triggered","pep_flagged"]:
            assert f in s, f"Missing: {f}"

    def test_section3_has_failure_fields(self):
        s = self._get_report()["section_3_failures"]
        for f in ["ekyc_failed","fallback_kyc_cases","fallback_approved",
                  "fallback_rejected","trigger_breakdown"]:
            assert f in s, f"Missing: {f}"

    def test_section4_has_screening_fields(self):
        s = self._get_report()["section_4_screening"]
        for f in ["total_screened","pep_hits","blocked"]:
            assert f in s, f"Missing: {f}"

    def test_section5_has_cmi_fields(self):
        s = self._get_report()["section_5_cmi_bo"]
        for f in ["bo_accounts_opened","bo_accounts_active","simplified_bo","regular_bo"]:
            assert f in s, f"Missing: {f}"

    def test_section7_has_summary(self):
        s = self._get_report()["section_7_summary"]
        for f in ["total_ekyc_attempts","total_accounts_opened",
                  "total_failures","compliance_rate_pct"]:
            assert f in s, f"Missing: {f}"

    def test_compliance_rate_between_0_and_100(self):
        s = self._get_report()["section_7_summary"]
        rate = s["compliance_rate_pct"]
        assert 0 <= rate <= 100

# ══════════════════════════════════════════════════════════════════════════
# 3. CSV Download (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestCSVDownload:
    def test_csv_download_200(self):
        r = generate_report()
        rid = r.json()["report"]["report_id"]
        r2 = client.get(f"{BASE}/{rid}/csv")
        assert r2.status_code == 200

    def test_csv_content_type(self):
        r = generate_report()
        rid = r.json()["report"]["report_id"]
        r2 = client.get(f"{BASE}/{rid}/csv")
        assert "text/csv" in r2.headers["content-type"]

    def test_csv_has_bfiu_header(self):
        r = generate_report()
        rid = r.json()["report"]["report_id"]
        r2 = client.get(f"{BASE}/{rid}/csv")
        assert "BFIU" in r2.text
        assert "SECTION 1" in r2.text

# ══════════════════════════════════════════════════════════════════════════
# 4. Get, List, Current Month (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestGetListCurrentMonth:
    def test_get_report_by_id(self):
        r = generate_report()
        rid = r.json()["report"]["report_id"]
        r2 = client.get(f"{BASE}/{rid}")
        assert r2.status_code == 200
        assert r2.json()["report"]["report_id"] == rid

    def test_get_nonexistent_404(self):
        assert client.get(f"{BASE}/BFIU-NOTEXIST").status_code == 404

    def test_list_all_200(self):
        generate_report()
        r = client.get(f"{BASE}/list/all")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_current_month_200(self):
        r = client.get(f"{BASE}/current-month")
        assert r.status_code == 200
        assert "report_id" in r.json()["report"]
