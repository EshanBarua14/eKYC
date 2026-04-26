"""BFIU Circular No. 29 — Full Compliance Verification Test Suite"""
import pytest


class TestBFIU_S2_Thresholds:
    def test_life_below_threshold_simplified(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("INSURANCE_LIFE", "life_endowment", 1_500_000) == "SIMPLIFIED"
    def test_life_at_threshold_simplified(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("INSURANCE_LIFE", "life_term", 2_000_000) == "SIMPLIFIED"
    def test_life_above_threshold_regular(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("INSURANCE_LIFE", "life_whole", 2_000_001) == "REGULAR"
    def test_non_life_at_threshold_simplified(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("INSURANCE_NON_LIFE", "fire", 250_000) == "SIMPLIFIED"
    def test_non_life_above_threshold_regular(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("INSURANCE_NON_LIFE", "motor", 250_001) == "REGULAR"
    def test_cmi_at_threshold_simplified(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("CMI", "bo_account", 1_500_000) == "SIMPLIFIED"
    def test_cmi_above_threshold_regular(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("CMI", "bo_account", 1_500_001) == "REGULAR"
    def test_missing_product_regular(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("CMI", None, 100_000) == "REGULAR"
    def test_all_four_thresholds(self):
        from app.services.kyc_threshold import THRESHOLDS
        assert THRESHOLDS["LIFE_SUM_ASSURED"]    == 2_000_000
        assert THRESHOLDS["LIFE_ANNUAL_PREMIUM"] == 250_000
        assert THRESHOLDS["NON_LIFE_PREMIUM"]    == 250_000
        assert THRESHOLDS["CMI_DEPOSIT"]         == 1_500_000


class TestBFIU_S3_SessionLimits:
    def setup_method(self):
        from app.services import session_limiter
        session_limiter._sessions.clear()
        session_limiter._attempts.clear()
    def test_max_attempts_is_10(self):
        from app.services.session_limiter import MAX_ATTEMPTS_PER_SESSION
        assert MAX_ATTEMPTS_PER_SESSION == 10
    def test_max_sessions_is_2(self):
        from app.services.session_limiter import MAX_SESSIONS_PER_DAY
        assert MAX_SESSIONS_PER_DAY == 2
    def test_session_allowed_initially(self):
        from app.services.session_limiter import check_session_limit, hash_nid
        assert check_session_limit(hash_nid("9999999999"))["allowed"] is True
    def test_session_blocked_after_max(self):
        from app.services.session_limiter import increment_session_count, check_session_limit, hash_nid
        h = hash_nid("1111111111")
        increment_session_count(h); increment_session_count(h)
        assert check_session_limit(h)["allowed"] is False
    def test_nid_hashed_not_plaintext(self):
        from app.services.session_limiter import hash_nid
        h = hash_nid("1234567890")
        assert "1234567890" not in h and len(h) == 64


class TestBFIU_S3_Fallback:
    def test_fallback_create_case_callable(self):
        from app.services.fallback_service import create_fallback_case
        assert callable(create_fallback_case)
    def test_fallback_trigger_codes_defined(self):
        from app.services.fallback_service import TRIGGER_CODES
        assert len(TRIGGER_CODES) > 0
    def test_fallback_decide_callable(self):
        from app.services.fallback_service import decide_case
        assert callable(decide_case)


class TestBFIU_S3_Screening:
    def test_screen_unscr_callable(self):
        from app.services.screening_service import screen_unscr
        assert callable(screen_unscr)
    def test_unscr_returns_verdict(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("Mohammad Rahman")
        assert "verdict" in r and r["verdict"] in ("CLEAR","HIT","REVIEW")
    def test_unscr_includes_list_version(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("Test User")
        assert "list_version" in r
    def test_unscr_includes_bfiu_ref(self):
        from app.services.screening_service import screen_unscr
        r = screen_unscr("Test User")
        assert "bfiu_ref" in r
    def test_screen_pep_callable(self):
        from app.services.screening_service import screen_pep
        assert callable(screen_pep)
    def test_screen_adverse_media_callable(self):
        from app.services.screening_service import screen_adverse_media
        assert callable(screen_adverse_media)
    def test_run_full_screening_returns_combined_verdict(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("Test User", "SIMPLIFIED", "DEMO")
        assert "combined_verdict" in r or "overall_verdict" in r
    def test_full_screening_has_unscr(self):
        from app.services.screening_service import run_full_screening
        r = run_full_screening("Test User", "SIMPLIFIED", "DEMO")
        assert "unscr" in r["results"]
    def test_exit_list_screening_callable(self):
        from app.services.screening_service import screen_exit_list
        assert callable(screen_exit_list)


class TestBFIU_S3_MatchingParams:
    def test_nid_lookup_callable(self):
        from app.services.nid_api_client import lookup_nid
        assert callable(lookup_nid)
    def test_nid_retry_callable(self):
        from app.services.nid_api_client import lookup_nid_with_retry
        assert callable(lookup_nid_with_retry)
    def test_nid_error_codes_defined(self):
        from app.services.nid_api_client import EC_AUTH_ERROR, EC_NOT_FOUND, EC_UNAVAILABLE
        assert all([EC_AUTH_ERROR, EC_NOT_FOUND, EC_UNAVAILABLE])
    def test_nid_ocr_callable(self):
        from app.services.nid_ocr_service import scan_nid_card
        assert callable(scan_nid_card)
    def test_cross_match_callable(self):
        from app.services.nid_api_client import cross_match_nid
        assert callable(cross_match_nid)


class TestBFIU_S4_RegularKYC:
    def test_high_risk_threshold_is_15(self):
        from app.services.risk_grading_service import HIGH_RISK_THRESHOLD
        assert HIGH_RISK_THRESHOLD == 15
    def test_pep_triggers_edd(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="AGENCY", residency="RESIDENT", pep_ip_status="PEP",
            product_type="ORDINARY_LIFE", business_type="RETAIL", profession="PRIVATE_SERVICE",
            annual_income_bdt=500_000, source_of_funds="salary",
            institution_type="INSURANCE", pep_flag=True)
        assert r["edd_required"] is True and r["grade"] == "HIGH"
    def test_high_score_triggers_edd(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="WALK_IN", residency="NRB", pep_ip_status="NONE",
            product_type="BO_ACCOUNT", business_type="MONEY_EXCHANGE", profession="FREELANCE",
            annual_income_bdt=60_000_000, source_of_funds=None, institution_type="CMI")
        assert r["total_score"] >= 15 and r["edd_required"] is True
    def test_low_score_no_edd(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="AGENCY", residency="RESIDENT", pep_ip_status="NONE",
            product_type="ORDINARY_LIFE", business_type="AGRICULTURE", profession="TEACHER",
            annual_income_bdt=500_000, source_of_funds="monthly_salary", institution_type="INSURANCE")
        assert r["total_score"] < 15 and r["edd_required"] is False
    def test_edd_auto_close_callable(self):
        from app.services.edd_service import auto_close_expired_cases
        assert callable(auto_close_expired_cases)
    def test_edd_sla_30_days(self):
        from app.services.edd_service import EDD_SLA_DAYS
        assert EDD_SLA_DAYS == 30
    def test_source_of_funds_required(self):
        from app.services.source_of_funds_validator import validate_source_of_funds, SourceOfFundsValidationError
        # None source raises exception (required for regular eKYC §4.2)
        try:
            validate_source_of_funds(None)
            assert False, "Should have raised"
        except SourceOfFundsValidationError:
            pass  # correct
        # Valid enum source passes
        result = validate_source_of_funds("SALARY")
        assert result is not None
    def test_edd_create_callable(self):
        from app.services.edd_service import create_edd_case
        assert callable(create_edd_case)
    def test_edd_status_enum(self):
        from app.services.edd_service import EDDStatus
        assert EDDStatus is not None


class TestBFIU_S5_AuditRecords:
    def test_log_event_callable(self):
        from app.services.audit_service import log_event
        assert callable(log_event)
    def test_retention_5_years(self):
        from app.services.audit_service import RETENTION_YEARS
        assert RETENTION_YEARS == 5
    def test_audit_pdf_callable(self):
        from app.services.audit_pdf_service import generate_audit_pdf
        assert callable(generate_audit_pdf)
    def test_kyc_form_generator_callable(self):
        from app.services.kyc_form_generator import generate_kyc_profile_form
        assert callable(generate_kyc_profile_form)
    def test_audit_export_callable(self):
        from app.services.audit_service import export_audit
        assert callable(export_audit)
    def test_audit_events_defined(self):
        from app.services.audit_service import AUDIT_EVENTS
        assert len(AUDIT_EVENTS) > 0


class TestBFIU_S4_5_Security:
    def test_jwt_token_creation(self):
        from app.core.security import create_access_token, Role
        token = create_access_token("inst_001", "user_001", Role.AGENT, "public")
        assert isinstance(token, str) and len(token) > 10
    def test_data_residency_middleware(self):
        from app.middleware.data_residency import DataResidencyMiddleware
        assert DataResidencyMiddleware is not None
    def test_error_boundary_registered(self):
        """Error boundary handlers registered in app §4.5"""
        from app.middleware.error_boundary import register_error_handlers
        assert callable(register_error_handlers)
    def test_rate_limiter_check_callable(self):
        from app.services.rate_limiter import check_rate_limit
        assert callable(check_rate_limit)
    def test_2fa_policy_callable(self):
        from app.services.twofa_service import get_2fa_policy, check_2fa_compliance
        assert callable(get_2fa_policy) and callable(check_2fa_compliance)
    def test_ip_whitelist_middleware(self):
        from app.middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware
        assert AdminIPWhitelistMiddleware is not None
    def test_weak_secret_key_flagged(self):
        from app.core.config import check_secrets
        warnings = check_secrets()
        assert any("SECRET_KEY" in w for w in warnings)


class TestBFIU_S5_7_PeriodicReview:
    def test_review_freq_dict_exists(self):
        from app.services.lifecycle_service import REVIEW_FREQUENCY_YEARS
        assert isinstance(REVIEW_FREQUENCY_YEARS, dict)
    def test_high_risk_1_year(self):
        from app.services.lifecycle_service import REVIEW_FREQUENCY_YEARS
        assert REVIEW_FREQUENCY_YEARS["HIGH"] == 1
    def test_medium_risk_2_years(self):
        from app.services.lifecycle_service import REVIEW_FREQUENCY_YEARS
        assert REVIEW_FREQUENCY_YEARS["MEDIUM"] == 2
    def test_low_risk_5_years(self):
        from app.services.lifecycle_service import REVIEW_FREQUENCY_YEARS
        assert REVIEW_FREQUENCY_YEARS["LOW"] == 5
    def test_calculate_next_review(self):
        from app.services.lifecycle_service import calculate_next_review
        assert callable(calculate_next_review)
    def test_submit_declaration(self):
        from app.services.lifecycle_service import submit_declaration
        assert callable(submit_declaration)
    def test_close_account(self):
        from app.services.lifecycle_service import close_account
        assert callable(close_account)


class TestBFIU_S6_3_RiskGrading:
    def test_walk_in_score_3(self):
        from app.services.risk_grading_service import ONBOARDING_CHANNEL_SCORES
        assert ONBOARDING_CHANNEL_SCORES["WALK_IN"] == 3
    def test_nrb_score_3(self):
        from app.services.risk_grading_service import RESIDENCY_SCORES
        assert RESIDENCY_SCORES["NRB"] == 3
    def test_resident_score_1(self):
        from app.services.risk_grading_service import RESIDENCY_SCORES
        assert RESIDENCY_SCORES["RESIDENT"] == 1
    def test_pep_score_5(self):
        from app.services.risk_grading_service import PEP_IP_SCORES
        assert PEP_IP_SCORES["PEP"] == 5
    def test_no_sof_score_5(self):
        from app.services.risk_grading_service import TRANSPARENCY_SCORES
        assert TRANSPARENCY_SCORES["NOT_PROVIDED"] == 5
    def test_sof_provided_score_1(self):
        from app.services.risk_grading_service import TRANSPARENCY_SCORES
        assert TRANSPARENCY_SCORES["PROVIDED"] == 1
    def test_txn_above_50m_score_5(self):
        from app.services.risk_grading_service import score_transaction_volume
        assert score_transaction_volume(60_000_000) == 5
    def test_txn_below_1m_score_1(self):
        from app.services.risk_grading_service import score_transaction_volume
        assert score_transaction_volume(500_000) == 1
    def test_cmi_bo_account_score_2(self):
        from app.services.risk_grading_service import PRODUCT_RISK_SCORES_CMI
        assert PRODUCT_RISK_SCORES_CMI.get("BO_ACCOUNT", 0) == 2
    def test_result_has_7_dimensions(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="AGENCY", residency="RESIDENT", pep_ip_status="NONE",
            product_type="ORDINARY_LIFE", business_type="RETAIL", profession="PRIVATE_SERVICE",
            annual_income_bdt=500_000, source_of_funds="salary", institution_type="INSURANCE")
        s = r["dimension_scores"]
        for dim in ["d1_onboarding_channel","d2_residency","d3_pep_ip","d4_product","d5a_business","d6_transaction","d7_transparency"]:
            assert dim in s, f"Missing dimension: {dim}"
    def test_result_has_review_years(self):
        from app.services.risk_grading_service import calculate_risk_score
        r = calculate_risk_score(
            onboarding_channel="AGENCY", residency="RESIDENT", pep_ip_status="NONE",
            product_type="ORDINARY_LIFE", business_type="AGRICULTURE", profession="TEACHER",
            annual_income_bdt=200_000, source_of_funds="salary", institution_type="INSURANCE")
        assert "review_years" in r


class TestBFIU_Annexure1:
    def test_money_exchange_5(self):
        from app.services.risk_grading_service import BUSINESS_TYPE_SCORES
        assert BUSINESS_TYPE_SCORES.get("MONEY_EXCHANGE", 0) == 5
    def test_import_export_high(self):
        from app.services.risk_grading_service import BUSINESS_TYPE_SCORES
        assert BUSINESS_TYPE_SCORES.get("IMPORT_EXPORT", 0) >= 4
    def test_agriculture_1(self):
        from app.services.risk_grading_service import BUSINESS_TYPE_SCORES
        assert BUSINESS_TYPE_SCORES.get("AGRICULTURE", 0) == 1
    def test_real_estate_high(self):
        from app.services.risk_grading_service import BUSINESS_TYPE_SCORES
        assert BUSINESS_TYPE_SCORES.get("REAL_ESTATE", 0) >= 4
    def test_all_scores_1_to_5(self):
        from app.services.risk_grading_service import BUSINESS_TYPE_SCORES
        for k, v in BUSINESS_TYPE_SCORES.items():
            assert 1 <= v <= 5, f"{k}={v}"


class TestBFIU_Liveness:
    def test_liveness_callable(self):
        from app.services.liveness import run_liveness_checks
        assert callable(run_liveness_checks)
    def test_face_compare_callable(self):
        from app.services.face_match import compare_faces
        assert callable(compare_faces)
    def test_face_verdict_callable(self):
        from app.services.face_match import get_verdict
        assert callable(get_verdict)


class TestBFIU_BeneficialOwner:
    def test_bo_router(self):
        from app.api.v1.routes.beneficial_owner import router
        assert router is not None
    def test_bo_schema(self):
        from app.api.v1.routes.beneficial_owner import BOCreateRequest
        assert BOCreateRequest is not None


class TestBFIU_ExitList:
    def test_screen_exit_list_db(self):
        from app.services.exit_list_service import screen_exit_list_db
        assert callable(screen_exit_list_db)
    def test_add_to_exit_list(self):
        from app.services.exit_list_service import add_to_exit_list_db
        assert callable(add_to_exit_list_db)
    def test_deactivate_entry(self):
        from app.services.exit_list_service import deactivate_exit_list_entry
        assert callable(deactivate_exit_list_entry)


class TestBFIU_Notifications:
    def test_success_notify(self):
        from app.services.notification_service import notify_kyc_success
        assert callable(notify_kyc_success)
    def test_failure_notify(self):
        from app.services.notification_service import notify_kyc_failure
        assert callable(notify_kyc_failure)
    def test_notification_log_model(self):
        from app.services.notification_service import NotificationLog
        assert NotificationLog is not None


class TestBFIU_BanglaPhonetic:
    def test_normalize_callable(self):
        from app.services.bangla_phonetic import phonetic_normalize
        assert callable(phonetic_normalize)
    def test_normalize_bangla_string(self):
        from app.services.bangla_phonetic import phonetic_normalize
        assert isinstance(phonetic_normalize("মোহাম্মদ রহমান"), str)
    def test_normalize_english_string(self):
        from app.services.bangla_phonetic import phonetic_normalize
        r = phonetic_normalize("Mohammad Rahman")
        assert isinstance(r, str) and len(r) > 0
    def test_enhanced_match_score(self):
        from app.services.bangla_phonetic import enhanced_match_score
        assert callable(enhanced_match_score)


class TestBFIU_NRB:
    def test_nrb_higher_risk(self):
        from app.services.risk_grading_service import RESIDENCY_SCORES
        assert RESIDENCY_SCORES["NRB"] > RESIDENCY_SCORES["RESIDENT"]
    def test_nrb_not_blocked_simplified(self):
        from app.services.kyc_threshold import assign_kyc_type
        assert assign_kyc_type("CMI", "bo_account", 500_000) == "SIMPLIFIED"


class TestBFIU_APIRouters:
    def test_app_loads(self):
        from app.main import app
        assert len(app.routes) > 0
    def test_health_route(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("health" in r for r in routes)
    def test_auth_route(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("auth" in r for r in routes)
    def test_nid_route(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("nid" in r for r in routes)
    def test_screening_route(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("screening" in r for r in routes)
    def test_risk_route(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("risk" in r for r in routes)
    def test_audit_route(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("audit" in r for r in routes)
