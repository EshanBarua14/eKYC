"""
test_cmi.py - M20 CMI/BO Account Support
Tests: open account, thresholds, products, get, list, 2026 routing
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/cmi"

def open_bo(session_id, verdict="MATCHED", product="BO_INDIVIDUAL",
            deposit=500_000, risk_grade="LOW", pep=False, confidence=87.5):
    return client.post(f"{BASE}/bo/open", json={
        "session_id":     session_id,
        "kyc_verdict":    verdict,
        "confidence":     confidence,
        "full_name":      "Md. Test Investor",
        "nid_hash":       "abc123hash",
        "mobile":         "01712345678",
        "date_of_birth":  "1990-01-15",
        "product_type":   product,
        "deposit_amount": deposit,
        "risk_grade":     risk_grade,
        "pep_flag":       pep,
        "institution_id": "inst_cmi_01",
        "agent_id":       "agent_01",
    })

# ══════════════════════════════════════════════════════════════════════════
# 1. Open BO Account (7 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestOpenBO:
    def test_open_returns_201(self):
        r = open_bo("sess_cmi_01")
        assert r.status_code == 201

    def test_open_has_bo_number(self):
        r = open_bo("sess_cmi_02")
        assert "bo_number" in r.json()["bo_account"]
        assert r.json()["bo_account"]["bo_number"].startswith("1201")

    def test_open_has_cdbl_ref(self):
        r = open_bo("sess_cmi_03")
        assert "cdbl_ref" in r.json()["bo_account"]
        assert r.json()["bo_account"]["cdbl_ref"].startswith("CDBL-")

    def test_low_risk_below_threshold_auto_approved(self):
        r = open_bo("sess_cmi_04", deposit=500_000, risk_grade="LOW")
        assert r.json()["bo_account"]["status"] == "ACTIVE"
        assert r.json()["bo_account"]["auto_approved"] is True

    def test_high_risk_routes_to_pending_review(self):
        r = open_bo("sess_cmi_05", risk_grade="HIGH")
        assert r.json()["bo_account"]["status"] == "PENDING_REVIEW"
        assert r.json()["bo_account"]["auto_approved"] is False

    def test_failed_verdict_422(self):
        r = open_bo("sess_cmi_06", verdict="FAILED", confidence=15.0)
        assert r.status_code == 422

    def test_duplicate_session_returns_existing(self):
        open_bo("sess_cmi_dup")
        r = open_bo("sess_cmi_dup")
        assert r.status_code == 201
        assert r.json()["already_exists"] is True

# ══════════════════════════════════════════════════════════════════════════
# 2. 2026 Threshold Routing (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestThresholdRouting:
    def test_below_threshold_simplified(self):
        r = open_bo("sess_thr_01", deposit=1_000_000)
        assert r.json()["bo_account"]["kyc_type"] == "SIMPLIFIED"

    def test_at_threshold_simplified(self):
        r = open_bo("sess_thr_02", deposit=1_500_000)
        assert r.json()["bo_account"]["kyc_type"] == "SIMPLIFIED"

    def test_above_threshold_regular(self):
        r = open_bo("sess_thr_03", deposit=1_500_001)
        assert r.json()["bo_account"]["kyc_type"] == "REGULAR"

    def test_pep_always_regular(self):
        r = open_bo("sess_thr_04", deposit=100_000, pep=True)
        assert r.json()["bo_account"]["kyc_type"] == "REGULAR"

# ══════════════════════════════════════════════════════════════════════════
# 3. Product Types (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestProducts:
    def test_bo_individual(self):
        r = open_bo("sess_prod_01", product="BO_INDIVIDUAL")
        assert r.json()["bo_account"]["cdbl_code"] == "BO-IND"

    def test_bo_joint(self):
        r = open_bo("sess_prod_02", product="BO_JOINT")
        assert r.json()["bo_account"]["cdbl_code"] == "BO-JNT"

    def test_bo_nrb_always_regular(self):
        r = open_bo("sess_prod_03", product="BO_NRB")
        assert r.json()["bo_account"]["kyc_type"] == "REGULAR"

    def test_margin_account_always_regular(self):
        r = open_bo("sess_prod_04", product="MARGIN_ACCOUNT", deposit=500_000)
        assert r.json()["bo_account"]["kyc_type"] == "REGULAR"

# ══════════════════════════════════════════════════════════════════════════
# 4. Get & List (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestGetList:
    def test_get_by_bo_number(self):
        r = open_bo("sess_get_01")
        bo_num = r.json()["bo_account"]["bo_number"]
        r2 = client.get(f"{BASE}/bo/{bo_num}")
        assert r2.status_code == 200
        assert r2.json()["bo_account"]["bo_number"] == bo_num

    def test_get_by_session(self):
        open_bo("sess_get_02")
        r = client.get(f"{BASE}/bo/session/sess_get_02")
        assert r.status_code == 200
        assert r.json()["bo_account"]["session_id"] == "sess_get_02"

    def test_get_nonexistent_404(self):
        assert client.get(f"{BASE}/bo/1201999999999").status_code == 404

    def test_list_accounts_200(self):
        r = client.get(f"{BASE}/bo/list")
        assert r.status_code == 200
        assert "accounts" in r.json()

# ══════════════════════════════════════════════════════════════════════════
# 5. Thresholds & Products catalog (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestThresholdsAndCatalog:
    def test_thresholds_200(self):
        assert client.get(f"{BASE}/thresholds").status_code == 200

    def test_thresholds_2026_values(self):
        r = client.get(f"{BASE}/thresholds")
        d = r.json()
        assert d["simplified_max_bdt"] == 1_500_000
        assert d["regular_min_bdt"]    == 1_500_001
        assert d["bfiu_ref"] is not None  # threshold_2026 flag is on account record

    def test_products_200(self):
        assert client.get(f"{BASE}/products").status_code == 200

    def test_products_has_all_types(self):
        r = client.get(f"{BASE}/products")
        products = r.json()["products"]
        for p in ["BO_INDIVIDUAL","BO_JOINT","BO_NRB","MARGIN_ACCOUNT","PORTFOLIO_MGT"]:
            assert p in products, f"Missing product: {p}"
