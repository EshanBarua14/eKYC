"""
M36 — Fingerprint SDK Service Tests
Multi-device abstract interface: Mantra, Morpho, Startek, DigitalPersona.
"""
import pytest
from unittest.mock import patch


# ══════════════════════════════════════════════════════════════════════════
# 1. Abstract interface
# ══════════════════════════════════════════════════════════════════════════
class TestFingerprintSDKBase:
    def test_all_providers_in_registry(self):
        from app.services.fingerprint_service import HARDWARE_PROVIDERS
        assert "MANTRA"         in HARDWARE_PROVIDERS
        assert "MORPHO"         in HARDWARE_PROVIDERS
        assert "STARTEK"        in HARDWARE_PROVIDERS
        assert "DIGITALPERSONA" in HARDWARE_PROVIDERS

    def test_all_providers_have_provider_name(self):
        from app.services.fingerprint_service import HARDWARE_PROVIDERS
        for name, cls in HARDWARE_PROVIDERS.items():
            assert hasattr(cls, "PROVIDER_NAME")
            assert cls.PROVIDER_NAME == name

    def test_all_providers_have_supported_models(self):
        from app.services.fingerprint_service import HARDWARE_PROVIDERS
        for name, cls in HARDWARE_PROVIDERS.items():
            assert hasattr(cls, "SUPPORTED_MODELS")
            assert len(cls.SUPPORTED_MODELS) > 0

    def test_all_providers_have_is_available(self):
        from app.services.fingerprint_service import HARDWARE_PROVIDERS
        for name, cls in HARDWARE_PROVIDERS.items():
            assert callable(cls.is_available)

    def test_all_providers_have_capture(self):
        from app.services.fingerprint_service import HARDWARE_PROVIDERS
        for name, cls in HARDWARE_PROVIDERS.items():
            assert callable(cls.capture)

    def test_all_providers_have_get_device_info(self):
        from app.services.fingerprint_service import HARDWARE_PROVIDERS
        for name, cls in HARDWARE_PROVIDERS.items():
            info = cls.get_device_info()
            assert "provider"  in info
            assert "available" in info
            assert "supported_models" in info


# ══════════════════════════════════════════════════════════════════════════
# 2. Mantra scanner
# ══════════════════════════════════════════════════════════════════════════
class TestMantraScanner:
    def test_supported_models(self):
        from app.services.fingerprint_service import MantraScanner
        assert "MFS100" in MantraScanner.SUPPORTED_MODELS
        assert "MFS500" in MantraScanner.SUPPORTED_MODELS
        assert "L1"     in MantraScanner.SUPPORTED_MODELS

    def test_is_available_returns_bool(self):
        from app.services.fingerprint_service import MantraScanner
        assert isinstance(MantraScanner.is_available(), bool)

    def test_capture_raises_not_implemented_when_sdk_absent(self):
        from app.services.fingerprint_service import MantraScanner
        with patch.object(MantraScanner, "is_available", return_value=False):
            with pytest.raises(NotImplementedError):
                MantraScanner.capture()

    def test_capture_with_quality_check_returns_dict(self):
        from app.services.fingerprint_service import MantraScanner
        with pytest.raises(NotImplementedError):
            MantraScanner.capture_with_quality_check()


# ══════════════════════════════════════════════════════════════════════════
# 3. Morpho scanner
# ══════════════════════════════════════════════════════════════════════════
class TestMorphoScanner:
    def test_supported_models(self):
        from app.services.fingerprint_service import MorphoScanner
        assert "MSO1300"    in MorphoScanner.SUPPORTED_MODELS
        assert "MSO1350"    in MorphoScanner.SUPPORTED_MODELS
        assert "MSO300"     in MorphoScanner.SUPPORTED_MODELS
        assert "MSO_ULTRA"  in MorphoScanner.SUPPORTED_MODELS

    def test_is_available_returns_bool(self):
        from app.services.fingerprint_service import MorphoScanner
        assert isinstance(MorphoScanner.is_available(), bool)

    def test_capture_raises_not_implemented_when_sdk_absent(self):
        from app.services.fingerprint_service import MorphoScanner
        with pytest.raises(NotImplementedError):
            MorphoScanner.capture()

    def test_get_connected_devices_returns_list(self):
        from app.services.fingerprint_service import MorphoScanner
        assert isinstance(MorphoScanner.get_connected_devices(), list)

    def test_capture_dual_finger_raises_not_implemented(self):
        from app.services.fingerprint_service import MorphoScanner
        with pytest.raises(NotImplementedError):
            MorphoScanner.capture_dual_finger("RIGHT_INDEX", "RIGHT_MIDDLE")


# ══════════════════════════════════════════════════════════════════════════
# 4. Startek scanner
# ══════════════════════════════════════════════════════════════════════════
class TestStartekScanner:
    def test_supported_models(self):
        from app.services.fingerprint_service import StartekScanner
        assert "FM220U" in StartekScanner.SUPPORTED_MODELS
        assert "FM220"  in StartekScanner.SUPPORTED_MODELS
        assert "EM500"  in StartekScanner.SUPPORTED_MODELS

    def test_is_available_returns_bool(self):
        from app.services.fingerprint_service import StartekScanner
        assert isinstance(StartekScanner.is_available(), bool)

    def test_capture_raises_not_implemented_when_sdk_absent(self):
        from app.services.fingerprint_service import StartekScanner
        with pytest.raises(NotImplementedError):
            StartekScanner.capture()

    def test_get_device_serial_returns_none_when_unavailable(self):
        from app.services.fingerprint_service import StartekScanner
        assert StartekScanner.get_device_serial() is None


# ══════════════════════════════════════════════════════════════════════════
# 5. DigitalPersona scanner
# ══════════════════════════════════════════════════════════════════════════
class TestDigitalPersonaScanner:
    def test_supported_models(self):
        from app.services.fingerprint_service import DigitalPersonaScanner
        assert "U.are.U 4500" in DigitalPersonaScanner.SUPPORTED_MODELS
        assert "U.are.U 5160" in DigitalPersonaScanner.SUPPORTED_MODELS

    def test_is_available_returns_bool(self):
        from app.services.fingerprint_service import DigitalPersonaScanner
        assert isinstance(DigitalPersonaScanner.is_available(), bool)

    def test_capture_raises_not_implemented_when_sdk_absent(self):
        from app.services.fingerprint_service import DigitalPersonaScanner
        with pytest.raises(NotImplementedError):
            DigitalPersonaScanner.capture()


# ══════════════════════════════════════════════════════════════════════════
# 6. Auto-detect provider
# ══════════════════════════════════════════════════════════════════════════
class TestAutoDetectProvider:
    def test_auto_detect_returns_demo_when_no_hardware(self):
        from app.services.fingerprint_service import (
            auto_detect_provider, MantraScanner, MorphoScanner,
            StartekScanner, DigitalPersonaScanner
        )
        with patch.object(MantraScanner, "is_available", return_value=False),              patch.object(MorphoScanner, "is_available", return_value=False),              patch.object(StartekScanner, "is_available", return_value=False),              patch.object(DigitalPersonaScanner, "is_available", return_value=False):
            result = auto_detect_provider()
        assert result == "DEMO"

    def test_auto_detect_returns_string(self):
        from app.services.fingerprint_service import auto_detect_provider
        result = auto_detect_provider()
        assert isinstance(result, str)

    def test_get_available_providers_returns_list(self):
        from app.services.fingerprint_service import get_available_providers
        providers = get_available_providers()
        assert isinstance(providers, list)
        assert len(providers) >= 5   # DEMO + 4 hardware

    def test_get_available_providers_includes_demo(self):
        from app.services.fingerprint_service import get_available_providers
        providers = get_available_providers()
        names = [p["provider"] for p in providers]
        assert "DEMO" in names


# ══════════════════════════════════════════════════════════════════════════
# 7. Demo provider
# ══════════════════════════════════════════════════════════════════════════
class TestDemoProvider:
    def setup_method(self):
        from app.services.fingerprint_service import set_demo_scenario
        set_demo_scenario("MATCH")

    def test_demo_match_scenario(self):
        from app.services.fingerprint_service import _verify_demo
        result = _verify_demo("1234567890123", "1990-01-15", "RIGHT_INDEX")
        assert result["matched"] is True
        assert result["score"] > 50

    def test_demo_no_match_scenario(self):
        from app.services.fingerprint_service import _verify_demo, set_demo_scenario
        set_demo_scenario("NO_MATCH")
        result = _verify_demo("1234567890123", "1990-01-15", "RIGHT_INDEX")
        assert result["matched"] is False

    def test_demo_low_quality_scenario(self):
        from app.services.fingerprint_service import _verify_demo, set_demo_scenario
        set_demo_scenario("LOW_QUALITY")
        result = _verify_demo("1234567890123", "1990-01-15", "RIGHT_INDEX")
        assert result["quality"] < 30

    def test_demo_timeout_raises(self):
        from app.services.fingerprint_service import _verify_demo, set_demo_scenario
        set_demo_scenario("TIMEOUT")
        with pytest.raises(TimeoutError):
            _verify_demo("1234567890123", "1990-01-15", "RIGHT_INDEX")

    def test_set_demo_scenario_valid(self):
        from app.services.fingerprint_service import set_demo_scenario
        assert set_demo_scenario("NO_MATCH") is True

    def test_set_demo_scenario_invalid(self):
        from app.services.fingerprint_service import set_demo_scenario
        assert set_demo_scenario("INVALID_SCENARIO") is False


# ══════════════════════════════════════════════════════════════════════════
# 8. verify_fingerprint — main API
# ══════════════════════════════════════════════════════════════════════════
class TestVerifyFingerprint:
    def setup_method(self):
        from app.services.fingerprint_service import set_demo_scenario, _reset_session
        set_demo_scenario("MATCH")
        _reset_session("test_sess_fp_001")
        _reset_session("test_sess_fp_002")
        _reset_session("test_sess_fp_003")
        _reset_session("test_sess_fp_004")
        _reset_session("test_sess_fp_005")

    def test_match_returns_matched_verdict(self):
        from app.services.fingerprint_service import verify_fingerprint
        result = verify_fingerprint("test_sess_fp_001", "1234567890123", "1990-01-15", "")
        assert result["verdict"] == "MATCHED"
        assert result["matched"] is True

    def test_no_match_returns_no_match_verdict(self):
        from app.services.fingerprint_service import verify_fingerprint, set_demo_scenario
        set_demo_scenario("NO_MATCH")
        result = verify_fingerprint("test_sess_fp_002", "1234567890123", "1990-01-15", "")
        assert result["verdict"] == "NO_MATCH"
        assert result["matched"] is False

    def test_low_quality_returns_low_quality_verdict(self):
        from app.services.fingerprint_service import verify_fingerprint, set_demo_scenario
        set_demo_scenario("LOW_QUALITY")
        result = verify_fingerprint("test_sess_fp_003", "1234567890123", "1990-01-15", "")
        assert result["verdict"] == "LOW_QUALITY"

    def test_result_has_required_fields(self):
        from app.services.fingerprint_service import verify_fingerprint
        result = verify_fingerprint("test_sess_fp_004", "1234567890123", "1990-01-15", "")
        for field in ["session_id", "verdict", "matched", "score", "quality",
                      "attempt_number", "attempts_remaining", "provider",
                      "processing_ms", "bfiu_ref"]:
            assert field in result, f"Missing field: {field}"

    def test_attempt_number_increments(self):
        from app.services.fingerprint_service import verify_fingerprint
        r1 = verify_fingerprint("test_sess_fp_005", "1234567890123", "1990-01-15", "")
        r2 = verify_fingerprint("test_sess_fp_005", "1234567890123", "1990-01-15", "")
        assert r2["attempt_number"] == r1["attempt_number"] + 1

    def test_bfiu_ref_present(self):
        from app.services.fingerprint_service import verify_fingerprint
        result = verify_fingerprint("test_sess_fp_006", "1234567890123", "1990-01-15", "")
        assert "BFIU" in result["bfiu_ref"]

    def test_timeout_returns_provider_timeout_verdict(self):
        from app.services.fingerprint_service import verify_fingerprint, set_demo_scenario
        set_demo_scenario("TIMEOUT")
        result = verify_fingerprint("test_sess_fp_007", "1234567890123", "1990-01-15", "")
        assert result["verdict"] == "PROVIDER_TIMEOUT"


# ══════════════════════════════════════════════════════════════════════════
# 9. Provider status
# ══════════════════════════════════════════════════════════════════════════
class TestProviderStatus:
    def test_get_provider_status_returns_dict(self):
        from app.services.fingerprint_service import get_provider_status
        status = get_provider_status()
        assert isinstance(status, dict)

    def test_provider_status_has_bfiu_limits(self):
        from app.services.fingerprint_service import get_provider_status
        status = get_provider_status()
        assert "bfiu_limits" in status
        assert status["bfiu_limits"]["max_attempts_per_session"] == 10

    def test_provider_status_has_providers_list(self):
        from app.services.fingerprint_service import get_provider_status
        status = get_provider_status()
        assert "providers" in status
        assert len(status["providers"]) >= 5
