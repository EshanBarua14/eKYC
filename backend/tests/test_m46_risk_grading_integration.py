"""
test_m46_risk_grading_integration.py
Integration tests for Risk Grading API — CMI/Bank/Insurance institution types
BFIU Circular No. 29 — Section 6.3, Annexure-1
Date: 2026-04-21
"""
import pytest
import pyotp
from fastapi.testclient import TestClient

SECRET = "JBSWY3DPEHPK3PXP"

@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)

@pytest.fixture(scope="module")
def token(client):
    import app.api.v1.routes.auth as auth_module
    auth_module._demo_users.clear()
    client.post("/api/v1/auth/register", json={
        "email": "checker_m46@demo.ekyc",
        "phone": "+8801712345679",
        "full_name": "Risk Integration Checker",
        "role": "CHECKER",
        "password": "CheckerM46@2026",
    })
    from app.api.v1.routes.auth import _demo_users
    u = next((x for x in _demo_users if x.email == "checker_m46@demo.ekyc"), None)
    if u is None:
        try:
            from app.db.database import SessionLocal
            from app.db.models import User as UserModel
            _db = SessionLocal()
            u = _db.query(UserModel).filter_by(email="checker_m46@demo.ekyc").first()
            _db.close()
            if u:
                _db2 = SessionLocal()
                _db2.query(UserModel).filter_by(email="checker_m46@demo.ekyc").update(
                    {"totp_secret": SECRET, "totp_enabled": True})
                _db2.commit(); _db2.close()
                u.totp_secret = SECRET; u.totp_enabled = True
                _demo_users.append(u)
        except Exception as e:
            print(f"[m46 setup] DB fallback: {e}")
    if u:
        u.totp_secret = SECRET
        u.totp_enabled = True
    r = client.post("/api/v1/auth/token", json={
        "email": "checker_m46@demo.ekyc",
        "password": "CheckerM46@2026",
        "totp_code": pyotp.TOTP(SECRET).now(),
    })
    return r.json()["access_token"]

@pytest.fixture
def hdrs(token):
    return {"Authorization": f"Bearer {token}"}

def _grade(client, hdrs, **kwargs):
    defaults = dict(
        kyc_profile_id="test-profile",
        institution_type="CMI",
        onboarding_channel="AGENCY",
        residency="RESIDENT",
        pep_ip_status="NONE",
        product_type="BO_ACCOUNT",
        business_type="OTHER",
        profession="OTHER",
        annual_income_bdt=500000,
        source_of_funds="Salary",
        pep_flag=False,
        adverse_media=False,
    )
    defaults.update(kwargs)
    return client.post("/api/v1/risk/grade", json=defaults, headers=hdrs)


class TestCMIRiskGrading:
    def test_bo_account_returns_grade(self, client, hdrs):
        r = _grade(client, hdrs, institution_type="CMI", product_type="BO_ACCOUNT")
        assert r.status_code == 200
        assert r.json()["grade"] in ["LOW", "MEDIUM", "HIGH"]

    def test_margin_account_scores_higher_than_bo(self, client, hdrs):
        bo     = _grade(client, hdrs, product_type="BO_ACCOUNT").json()
        margin = _grade(client, hdrs, product_type="MARGIN_ACCOUNT").json()
        assert margin["total_score"] >= bo["total_score"]

    def test_simplified_kyc_threshold_15_lakh(self, client, hdrs):
        # Deposit <= 15L => eligible for simplified
        r = _grade(client, hdrs, annual_income_bdt=1_000_000)
        assert r.status_code == 200

    def test_regular_kyc_above_15_lakh(self, client, hdrs):
        r = _grade(client, hdrs, annual_income_bdt=20_000_000)
        data = r.json()
        assert data["total_score"] >= 3  # higher transaction volume score

    def test_nrb_investor_scores_higher(self, client, hdrs):
        resident = _grade(client, hdrs, residency="RESIDENT").json()
        nrb      = _grade(client, hdrs, residency="NRB").json()
        assert nrb["total_score"] > resident["total_score"]

    def test_pep_investor_forced_high(self, client, hdrs):
        r = _grade(client, hdrs, pep_flag=True, pep_ip_status="PEP")
        data = r.json()
        assert data["grade"] == "HIGH"
        assert data["edd_required"] is True
        assert data["pep_override"] is True

    def test_adverse_media_forced_high(self, client, hdrs):
        r = _grade(client, hdrs, adverse_media=True)
        assert r.json()["grade"] == "HIGH"

    def test_result_contains_bfiu_ref(self, client, hdrs):
        r = _grade(client, hdrs)
        assert "bfiu_ref" in r.json()
        assert "29" in r.json()["bfiu_ref"]

    def test_dimension_breakdown_present(self, client, hdrs):
        r = _grade(client, hdrs)
        dims = r.json()["dimension_scores"]
        for d in ["d1_onboarding_channel","d2_residency","d3_pep_ip",
                  "d4_product","d5a_business","d5b_profession",
                  "d6_transaction","d7_transparency"]:
            assert d in dims

    def test_review_years_present(self, client, hdrs):
        r = _grade(client, hdrs)
        assert "review_years" in r.json()


class TestBankRiskGrading:
    def test_bank_savings_account(self, client, hdrs):
        r = _grade(client, hdrs, institution_type="BANK", product_type="SAVINGS")
        assert r.status_code == 200

    def test_bank_current_account(self, client, hdrs):
        r = _grade(client, hdrs, institution_type="BANK", product_type="CURRENT")
        assert r.status_code == 200

    def test_money_exchange_business_high_risk(self, client, hdrs):
        r = _grade(client, hdrs,
                   institution_type="BANK",
                   business_type="MONEY_EXCHANGE",
                   annual_income_bdt=60_000_000,
                   source_of_funds=None)
        data = r.json()
        assert data["total_score"] >= 15
        assert data["grade"] == "HIGH"

    def test_government_employee_low_risk(self, client, hdrs):
        r = _grade(client, hdrs,
                   institution_type="BANK",
                   profession="GOVERNMENT_EMPLOYEE",
                   business_type="GOVERNMENT",
                   residency="RESIDENT",
                   annual_income_bdt=400_000,
                   source_of_funds="Salary")
        assert r.json()["grade"] in ["LOW", "MEDIUM"]


class TestInsuranceRiskGrading:
    def test_ordinary_life_low_risk(self, client, hdrs):
        r = _grade(client, hdrs,
                   institution_type="INSURANCE",
                   product_type="ORDINARY_LIFE",
                   profession="TEACHER",
                   annual_income_bdt=300_000,
                   source_of_funds="Salary")
        assert r.json()["grade"] in ["LOW", "MEDIUM"]

    def test_group_insurance_higher_than_ordinary(self, client, hdrs):
        ordinary = _grade(client, hdrs, institution_type="INSURANCE",
                          product_type="ORDINARY_LIFE").json()
        group    = _grade(client, hdrs, institution_type="INSURANCE",
                          product_type="GROUP").json()
        assert group["dimension_scores"]["d4_product"] >= \
               ordinary["dimension_scores"]["d4_product"]


class TestEDDWorkflow:
    def test_edd_created_for_high_risk(self, client, hdrs):
        r = client.post("/api/v1/risk/edd", json={
            "kyc_profile_id": "m46-profile-001",
            "institution_id": "inst-demo-001",
            "risk_score": 18,
            "risk_grade": "HIGH",
        }, headers=hdrs)
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "PENDING"
        assert "sla_deadline" in data

    def test_edd_rejected_for_medium_risk(self, client, hdrs):
        r = client.post("/api/v1/risk/edd", json={
            "kyc_profile_id": "m46-profile-002",
            "institution_id": "inst-demo-001",
            "risk_score": 10,
            "risk_grade": "MEDIUM",
        }, headers=hdrs)
        assert r.status_code == 422

    def test_edd_allowed_with_pep_override(self, client, hdrs):
        r = client.post("/api/v1/risk/edd", json={
            "kyc_profile_id": "m46-profile-003",
            "institution_id": "inst-demo-001",
            "risk_score": 5,
            "risk_grade": "LOW",
            "pep_override": True,
        }, headers=hdrs)
        assert r.status_code == 201

    def test_edd_allowed_with_adverse_media(self, client, hdrs):
        r = client.post("/api/v1/risk/edd", json={
            "kyc_profile_id": "m46-profile-004",
            "institution_id": "inst-demo-001",
            "risk_score": 5,
            "risk_grade": "LOW",
            "adverse_media": True,
        }, headers=hdrs)
        assert r.status_code == 201


class TestRiskFactorsAndThresholds:
    def test_factors_all_dimensions(self, client, hdrs):
        r = client.get("/api/v1/risk/factors", headers=hdrs)
        assert r.status_code == 200
        d = r.json()
        for key in ["d1_onboarding_channel","d2_residency","d3_pep_ip_status",
                    "d4_product_insurance","d4_product_cmi","d5a_business_type",
                    "d5b_profession","d7_transparency","d6_transaction_bands"]:
            assert key in d

    def test_thresholds_values(self, client, hdrs):
        r = client.get("/api/v1/risk/thresholds", headers=hdrs)
        assert r.status_code == 200
        d = r.json()
        assert d["high_risk_threshold"]   == 15
        assert d["medium_risk_threshold"] == 8
        assert d["review_frequency_years"]["HIGH"]   == 1
        assert d["review_frequency_years"]["MEDIUM"] == 2
        assert d["review_frequency_years"]["LOW"]    == 5

    def test_unauthenticated_blocked(self, client):
        r = client.get("/api/v1/risk/factors")
        assert r.status_code == 403
