"""
M8 - Risk Grading Engine Tests
Tests: scoring dimensions, grade thresholds, PEP override, EDD, API endpoints
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Scoring dimension tests
# ---------------------------------------------------------------------------
class TestScoringDimensions:
    def setup_method(self):
        from app.services.risk_grading_service import (
            calculate_risk_score, score_transaction_volume,
            ONBOARDING_CHANNEL_SCORES, RESIDENCY_SCORES,
            HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD,
        )
        self.score          = calculate_risk_score
        self.tx_volume      = score_transaction_volume
        self.channel_scores = ONBOARDING_CHANNEL_SCORES
        self.HIGH           = HIGH_RISK_THRESHOLD
        self.MEDIUM         = MEDIUM_RISK_THRESHOLD

    def _base(self, **kwargs):
        defaults = dict(
            onboarding_channel="AGENCY",
            residency="RESIDENT",
            pep_ip_status="NONE",
            product_type="ORDINARY_LIFE",
            business_type="OTHER",
            profession="OTHER",
            annual_income_bdt=500_000,
            source_of_funds="Salary",
            institution_type="INSURANCE",
            pep_flag=False,
            adverse_media=False,
        )
        defaults.update(kwargs)
        return self.score(**defaults)

    def test_walk_in_scores_higher_than_agency(self):
        agency  = self._base(onboarding_channel="AGENCY")
        walk_in = self._base(onboarding_channel="WALK_IN")
        assert walk_in["dimension_scores"]["d1_onboarding_channel"] >                agency["dimension_scores"]["d1_onboarding_channel"]

    def test_nrb_scores_higher_than_resident(self):
        resident = self._base(residency="RESIDENT")
        nrb      = self._base(residency="NRB")
        assert nrb["dimension_scores"]["d2_residency"] >                resident["dimension_scores"]["d2_residency"]

    def test_pep_scores_max(self):
        r = self._base(pep_ip_status="PEP")
        assert r["dimension_scores"]["d3_pep_ip"] == 5

    def test_no_pep_scores_zero(self):
        r = self._base(pep_ip_status="NONE")
        assert r["dimension_scores"]["d3_pep_ip"] == 0

    def test_group_product_scores_higher_than_ordinary(self):
        ordinary = self._base(product_type="ORDINARY_LIFE")
        group    = self._base(product_type="GROUP")
        assert group["dimension_scores"]["d4_product"] >                ordinary["dimension_scores"]["d4_product"]

    def test_missing_source_of_funds_scores_5(self):
        r = self._base(source_of_funds=None)
        assert r["dimension_scores"]["d7_transparency"] == 5

    def test_provided_source_of_funds_scores_1(self):
        r = self._base(source_of_funds="Employment income")
        assert r["dimension_scores"]["d7_transparency"] == 1

    def test_transaction_volume_below_1m(self):
        assert self.tx_volume(500_000) == 1

    def test_transaction_volume_1m_to_5m(self):
        assert self.tx_volume(2_000_000) == 2

    def test_transaction_volume_5m_to_50m(self):
        assert self.tx_volume(10_000_000) == 3

    def test_transaction_volume_above_50m(self):
        assert self.tx_volume(100_000_000) == 5

    def test_result_has_all_7_dimensions(self):
        r = self._base()
        dims = r["dimension_scores"]
        assert "d1_onboarding_channel" in dims
        assert "d2_residency" in dims
        assert "d3_pep_ip" in dims
        assert "d4_product" in dims
        assert "d5a_business" in dims
        assert "d5b_profession" in dims
        assert "d6_transaction" in dims
        assert "d7_transparency" in dims


# ---------------------------------------------------------------------------
# Grade threshold tests
# ---------------------------------------------------------------------------
class TestGradeThresholds:
    def setup_method(self):
        from app.services.risk_grading_service import (
            calculate_risk_score, _determine_grade,
            HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD,
        )
        self.score          = calculate_risk_score
        self.determine      = _determine_grade
        self.HIGH           = HIGH_RISK_THRESHOLD
        self.MEDIUM         = MEDIUM_RISK_THRESHOLD

    def test_high_risk_threshold_is_15(self):
        assert self.HIGH == 15

    def test_medium_risk_threshold_is_8(self):
        assert self.MEDIUM == 8

    def test_score_above_15_is_high(self):
        r = self.determine(15, False, False)
        assert r == "HIGH"

    def test_score_below_8_is_low(self):
        r = self.determine(5, False, False)
        assert r == "LOW"

    def test_score_8_to_14_is_medium(self):
        r = self.determine(10, False, False)
        assert r == "MEDIUM"

    def test_pep_flag_overrides_to_high(self):
        r = self.determine(3, True, False)
        assert r == "HIGH"

    def test_adverse_media_overrides_to_high(self):
        r = self.determine(3, False, True)
        assert r == "HIGH"

    def test_low_score_low_grade(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="AGENCY",
            residency="RESIDENT",
            pep_ip_status="NONE",
            product_type="ORDINARY_LIFE",
            business_type="AGRICULTURE",
            profession="GOVERNMENT_EMPLOYEE",
            annual_income_bdt=300_000,
            source_of_funds="Salary",
        )
        assert r["grade"] in ["LOW", "MEDIUM"]

    def test_high_risk_triggers_edd(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="WALK_IN",
            residency="NRB",
            pep_ip_status="PEP",
            product_type="GROUP",
            business_type="MONEY_EXCHANGE",
            profession="POLITICIAN",
            annual_income_bdt=100_000_000,
            source_of_funds=None,
            pep_flag=True,
        )
        assert r["grade"] == "HIGH"
        assert r["edd_required"] is True

    def test_review_frequency_high_is_1yr(self):
        from app.services.risk_grading_service import REVIEW_FREQUENCY
        assert REVIEW_FREQUENCY["HIGH"] == 1

    def test_review_frequency_medium_is_2yr(self):
        from app.services.risk_grading_service import REVIEW_FREQUENCY
        assert REVIEW_FREQUENCY["MEDIUM"] == 2

    def test_review_frequency_low_is_5yr(self):
        from app.services.risk_grading_service import REVIEW_FREQUENCY
        assert REVIEW_FREQUENCY["LOW"] == 5


# ---------------------------------------------------------------------------
# EDD case tests
# ---------------------------------------------------------------------------
class TestEDDCase:
    def setup_method(self):
        from app.services.risk_grading_service import create_edd_case
        self.create_edd = create_edd_case

    def test_edd_case_has_case_id(self):
        r = self.create_edd(
            "profile-001",
            {"total_score": 18, "grade": "HIGH", "pep_override": False, "adverse_media": False},
            "inst-001",
        )
        assert "case_id" in r
        assert len(r["case_id"]) == 36

    def test_edd_case_status_is_pending(self):
        r = self.create_edd(
            "profile-001",
            {"total_score": 18, "grade": "HIGH", "pep_override": False, "adverse_media": False},
            "inst-001",
        )
        assert r["status"] == "PENDING"

    def test_edd_case_has_sla_deadline(self):
        r = self.create_edd(
            "profile-001",
            {"total_score": 18, "grade": "HIGH", "pep_override": False, "adverse_media": False},
            "inst-001",
        )
        assert "sla_deadline" in r

    def test_edd_case_bfiu_ref(self):
        r = self.create_edd(
            "profile-001",
            {"total_score": 18, "grade": "HIGH", "pep_override": False, "adverse_media": False},
            "inst-001",
        )
        assert "4.3" in r["bfiu_ref"]


# ---------------------------------------------------------------------------
# Rescore tests
# ---------------------------------------------------------------------------
class TestRescore:
    def test_rescore_uses_profile_data(self):
        from app.services.risk_grading_service import rescore_profile
        profile = {
            "onboarding_channel": "WALK_IN",
            "residency":          "NRB",
            "pep_ip_status":      "NONE",
            "product_type":       "GROUP",
            "business_type":      "RETAIL",
            "profession":         "BUSINESS_OWNER",
            "monthly_income":     500000,
            "source_of_funds":    "Business",
            "institution_type":   "INSURANCE",
            "pep_flag":           False,
            "adverse_media":      False,
        }
        r = rescore_profile(profile)
        assert "total_score" in r
        assert "grade" in r
        assert r["total_score"] > 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
class TestRiskAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        self.client.post("/api/v1/auth/register", json={
            "email": "checker_risk@demo.com",
            "phone": "+8801712345678",
            "full_name": "Risk Checker",
            "role": "CHECKER",
            "password": "checker123",
        })
        r = self.client.post("/api/v1/auth/token", json={
            "email": "checker_risk@demo.com",
            "password": "checker123",
        })
        self.token   = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_grade_endpoint_returns_score(self):
        r = self.client.post("/api/v1/risk/grade", json={
            "kyc_profile_id":     "profile-001",
            "institution_type":   "INSURANCE",
            "onboarding_channel": "AGENCY",
            "residency":          "RESIDENT",
            "pep_ip_status":      "NONE",
            "product_type":       "ORDINARY_LIFE",
            "business_type":      "RETAIL",
            "profession":         "TEACHER",
            "annual_income_bdt":  600000,
            "source_of_funds":    "Salary",
        }, headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_score" in data
        assert "grade" in data
        assert data["grade"] in ["LOW", "MEDIUM", "HIGH"]

    def test_grade_high_risk_profile(self):
        r = self.client.post("/api/v1/risk/grade", json={
            "kyc_profile_id":     "profile-002",
            "onboarding_channel": "WALK_IN",
            "residency":          "NRB",
            "pep_ip_status":      "PEP",
            "product_type":       "GROUP",
            "business_type":      "MONEY_EXCHANGE",
            "profession":         "POLITICIAN",
            "annual_income_bdt":  100000000,
            "source_of_funds":    None,
            "pep_flag":           True,
        }, headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["grade"] == "HIGH"
        assert data["edd_required"] is True

    def test_edd_endpoint_creates_case(self):
        r = self.client.post("/api/v1/risk/edd", json={
            "kyc_profile_id": "profile-003",
            "institution_id": "inst-001",
            "risk_score":     18,
            "risk_grade":     "HIGH",
        }, headers=self.headers)
        assert r.status_code == 201
        assert "case_id" in r.json()

    def test_edd_rejected_for_non_high(self):
        r = self.client.post("/api/v1/risk/edd", json={
            "kyc_profile_id": "profile-004",
            "institution_id": "inst-001",
            "risk_score":     5,
            "risk_grade":     "LOW",
        }, headers=self.headers)
        assert r.status_code == 422

    def test_factors_endpoint(self):
        r = self.client.get("/api/v1/risk/factors", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "d1_onboarding_channel" in data
        assert "d5a_business_type" in data

    def test_thresholds_endpoint(self):
        r = self.client.get("/api/v1/risk/thresholds", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["high_risk_threshold"] == 15

    def test_unauthenticated_grade_fails(self):
        r = self.client.post("/api/v1/risk/grade", json={
            "kyc_profile_id": "x",
        })
        assert r.status_code == 403

    def test_rescore_endpoint(self):
        r = self.client.post("/api/v1/risk/rescore", json={
            "profile_data": {
                "onboarding_channel": "AGENCY",
                "residency":          "RESIDENT",
                "product_type":       "ORDINARY_LIFE",
                "business_type":      "RETAIL",
                "profession":         "TEACHER",
                "monthly_income":     50000,
                "source_of_funds":    "Salary",
            }
        }, headers=self.headers)
        assert r.status_code == 200
        assert "grade" in r.json()
