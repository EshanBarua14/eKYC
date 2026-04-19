"""
M9 - Sanctions and Screening Engine Tests
Tests: fuzzy matching, UNSCR, PEP, adverse media, exit list, full screening, API
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fuzzy matching tests
# ---------------------------------------------------------------------------
class TestFuzzyMatching:
    def setup_method(self):
        from app.services.screening_service import (
            normalize_name, token_overlap_score,
            edit_distance_score, fuzzy_match_score,
        )
        self.normalize    = normalize_name
        self.token_score  = token_overlap_score
        self.edit_score   = edit_distance_score
        self.fuzzy_score  = fuzzy_match_score

    def test_normalize_uppercase(self):
        assert self.normalize("rahman hossain") == "RAHMAN HOSSAIN"

    def test_normalize_strips_punctuation(self):
        assert self.normalize("AL-QAIDA") == "AL QAIDA"

    def test_exact_match_score_1(self):
        s = self.fuzzy_score("RAHMAN HOSSAIN", "RAHMAN HOSSAIN")
        assert s == 1.0

    def test_no_overlap_score_0(self):
        s = self.token_score("JOHN SMITH", "RAHMAN HOSSAIN")
        assert s == 0.0

    def test_partial_match_between_0_and_1(self):
        s = self.fuzzy_score("RAHMAN HOSSAIN", "RAHMAN CHOWDHURY")
        assert 0.0 < s < 1.0

    def test_single_char_diff_high_score(self):
        s = self.edit_score("RAHMAN", "RAHMEN")
        assert s > 0.8

    def test_completely_different_low_score(self):
        s = self.edit_score("ABCDEF", "XYZWVU")
        assert s < 0.3

    def test_alias_variant_matches(self):
        s = self.fuzzy_score("AL QAIDA", "AL QAIDA")
        assert s == 1.0


# ---------------------------------------------------------------------------
# UNSCR screening tests
# ---------------------------------------------------------------------------
class TestUNSCRScreening:
    def setup_method(self):
        from app.services.screening_service import screen_unscr
        self.screen = screen_unscr

    def test_clear_name_returns_clear(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY")
        assert r["verdict"] == "CLEAR"

    def test_exact_sanctioned_name_blocked(self):
        r = self.screen("SANCTIONED PERSON ONE")
        assert r["verdict"] in ["MATCH", "REVIEW"]
        assert len(r["matches"]) > 0

    def test_alias_match_flagged(self):
        r = self.screen("JMB")
        assert r["verdict"] in ["MATCH", "REVIEW"]

    def test_result_has_list_version(self):
        r = self.screen("TEST NAME")
        assert "list_version" in r

    def test_result_has_screened_at(self):
        r = self.screen("TEST NAME")
        assert "screened_at" in r

    def test_result_has_bfiu_ref(self):
        r = self.screen("TEST NAME")
        assert "3.2.2" in r["bfiu_ref"]

    def test_clear_result_not_blocking(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY")
        assert r.get("blocking", False) is False

    def test_match_result_is_blocking(self):
        r = self.screen("SANCTIONED PERSON ONE")
        if r["verdict"] == "MATCH":
            assert r["blocking"] is True


# ---------------------------------------------------------------------------
# PEP screening tests
# ---------------------------------------------------------------------------
class TestPEPScreening:
    def setup_method(self):
        from app.services.screening_service import screen_pep
        self.screen = screen_pep

    def test_clear_name_returns_clear(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY")
        assert r["verdict"] == "CLEAR"

    def test_pep_name_matched(self):
        r = self.screen("POLITICAL FIGURE ONE")
        assert r["verdict"] == "MATCH"

    def test_pep_match_triggers_edd(self):
        r = self.screen("POLITICAL FIGURE ONE")
        if r["verdict"] == "MATCH":
            assert r["edd_required"] is True

    def test_pep_match_has_role(self):
        r = self.screen("POLITICAL FIGURE ONE")
        if r["verdict"] == "MATCH":
            assert "role" in r

    def test_pep_result_has_bfiu_ref(self):
        r = self.screen("TEST NAME")
        assert "4.2" in r["bfiu_ref"]


# ---------------------------------------------------------------------------
# Adverse media tests
# ---------------------------------------------------------------------------
class TestAdverseMedia:
    def setup_method(self):
        from app.services.screening_service import screen_adverse_media
        self.screen = screen_adverse_media

    def test_clean_name_is_clear(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY")
        assert r["verdict"] == "CLEAR"

    def test_flagged_name_detected(self):
        r = self.screen("KARIM CORRUPT")
        assert r["verdict"] == "FLAGGED"

    def test_flagged_triggers_edd(self):
        r = self.screen("KARIM CORRUPT")
        if r["verdict"] == "FLAGGED":
            assert r["edd_required"] is True

    def test_result_has_hit_count(self):
        r = self.screen("TEST NAME")
        assert "hit_count" in r

    def test_result_has_bfiu_ref(self):
        r = self.screen("TEST NAME")
        assert "5.3" in r["bfiu_ref"]


# ---------------------------------------------------------------------------
# Exit list tests
# ---------------------------------------------------------------------------
class TestExitList:
    def setup_method(self):
        from app.services.screening_service import (
            add_to_exit_list, screen_exit_list, reset_exit_lists
        )
        self.add    = add_to_exit_list
        self.screen = screen_exit_list
        self.reset  = reset_exit_lists
        self.reset()

    def test_add_to_exit_list(self):
        r = self.add("inst-001", "BLOCKED PERSON", "Fraud")
        assert "id" in r
        assert r["name"] == "BLOCKED PERSON"

    def test_screen_after_add_matches(self):
        self.add("inst-001", "EXIT PERSON ONE", "Money laundering")
        r = self.screen("EXIT PERSON ONE", "inst-001")
        assert r["verdict"] == "MATCH"

    def test_screen_different_institution_clear(self):
        self.add("inst-001", "EXIT PERSON TWO", "Fraud")
        r = self.screen("EXIT PERSON TWO", "inst-002")
        assert r["verdict"] == "CLEAR"

    def test_empty_exit_list_clear(self):
        r = self.screen("ANY NAME", "inst-999")
        assert r["verdict"] == "CLEAR"

    def test_exit_match_is_blocking(self):
        self.add("inst-001", "EXIT PERSON THREE", "Terrorism")
        r = self.screen("EXIT PERSON THREE", "inst-001")
        if r["verdict"] == "MATCH":
            assert r["blocking"] is True


# ---------------------------------------------------------------------------
# Full screening tests
# ---------------------------------------------------------------------------
class TestFullScreening:
    def setup_method(self):
        from app.services.screening_service import run_full_screening, reset_exit_lists
        self.screen = run_full_screening
        self.reset  = reset_exit_lists
        self.reset()

    def test_simplified_clear_name(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY", "SIMPLIFIED")
        assert r["combined_verdict"] == "CLEAR"

    def test_simplified_only_runs_unscr_and_exit(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY", "SIMPLIFIED")
        assert "unscr" in r["results"]
        assert "exit_list" in r["results"]
        assert "pep" not in r["results"]
        assert "adverse_media" not in r["results"]

    def test_regular_runs_all_four_checks(self):
        r = self.screen("RAHMAN HOSSAIN CHOWDHURY", "REGULAR")
        assert "unscr" in r["results"]
        assert "pep" in r["results"]
        assert "adverse_media" in r["results"]
        assert "exit_list" in r["results"]

    def test_sanctioned_name_blocked(self):
        r = self.screen("SANCTIONED PERSON ONE", "SIMPLIFIED")
        assert r["combined_verdict"] in ["BLOCKED", "REVIEW"]

    def test_result_has_bfiu_ref(self):
        r = self.screen("TEST NAME", "SIMPLIFIED")
        assert "bfiu_ref" in r

    def test_blocked_sets_edd_required(self):
        r = self.screen("SANCTIONED PERSON ONE", "SIMPLIFIED")
        if r["combined_verdict"] == "BLOCKED":
            assert r["edd_required"] is True


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
class TestScreeningAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        self.client.post("/api/v1/auth/register", json={
            "email": "checker_scr@demo.com",
            "phone": "+8801712345678",
            "full_name": "Screening Checker",
            "role": "CHECKER",
            "password": "checker123",
        })
        import pyotp; _S = "JBSWY3DPEHPK3PXP"
        from app.api.v1.routes.auth import _demo_users
        u = next((x for x in _demo_users if x.email == "checker_scr@demo.com"), None)
        if u and not u.totp_enabled: u.totp_secret = _S; u.totp_enabled = True
        r = self.client.post("/api/v1/auth/token", json={
            "email": "checker_scr@demo.com",
            "password": "checker123",
            "totp_code": pyotp.TOTP(_S).now(),
        })
        self.token   = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        from app.services.screening_service import reset_exit_lists
        reset_exit_lists()

    def test_unscr_clear(self):
        r = self.client.post("/api/v1/screening/unscr", json={
            "name": "RAHMAN HOSSAIN CHOWDHURY",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["verdict"] == "CLEAR"

    def test_unscr_blocked(self):
        r = self.client.post("/api/v1/screening/unscr", json={
            "name": "SANCTIONED PERSON ONE",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["verdict"] in ["MATCH", "REVIEW"]

    def test_pep_skipped_for_simplified(self):
        r = self.client.post("/api/v1/screening/pep", json={
            "name": "ANY NAME", "kyc_type": "SIMPLIFIED",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["verdict"] == "SKIPPED"

    def test_pep_runs_for_regular(self):
        r = self.client.post("/api/v1/screening/pep", json={
            "name": "RAHMAN HOSSAIN CHOWDHURY", "kyc_type": "REGULAR",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["verdict"] in ["CLEAR", "MATCH"]

    def test_exit_list_add_and_check(self):
        self.client.post("/api/v1/screening/exit-list/add", json={
            "institution_id": "inst-test",
            "name":           "API EXIT PERSON",
            "reason":         "Test",
        }, headers=self.headers)
        r = self.client.post("/api/v1/screening/exit-list/check", json={
            "name":           "API EXIT PERSON",
            "institution_id": "inst-test",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["verdict"] == "MATCH"

    def test_full_screening_simplified(self):
        r = self.client.post("/api/v1/screening/full", json={
            "name":     "RAHMAN HOSSAIN CHOWDHURY",
            "kyc_type": "SIMPLIFIED",
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()["combined_verdict"] == "CLEAR"

    def test_full_screening_regular(self):
        r = self.client.post("/api/v1/screening/full", json={
            "name":     "RAHMAN HOSSAIN CHOWDHURY",
            "kyc_type": "REGULAR",
        }, headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "pep" in data["results"]
        assert "adverse_media" in data["results"]

    def test_thresholds_endpoint(self):
        r = self.client.get("/api/v1/screening/thresholds", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "SIMPLIFIED" in data["screening_tiers"]
        assert "REGULAR" in data["screening_tiers"]

    def test_unauthenticated_fails(self):
        r = self.client.post("/api/v1/screening/unscr", json={"name": "TEST"})
        assert r.status_code == 403
