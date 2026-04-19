"""
Fingerprint Verification Service — M36
BFIU Circular No. 29 — Section 3.2

Abstract SDK interface for multi-device support:
  DEMO          — synthetic results, no hardware needed (dev/CI)
  PORICHOY      — Porichoy API gateway (Bangladesh government)
  MANTRA        — Mantra MFS100 / MFS500 / L1
  MORPHO        — Idemia/Morpho MSO Series (MSO 1300, MSO 1350, MSO 300)
  STARTEK       — Startek FM220U / FM220 / EM500
  DIGITALPERSONA — DigitalPersona U.are.U 4500/5160
  AUTO          — auto-detect first available hardware

Hardware note:
  Frontend captures fingerprint → Base64 WSQ or ISO/ANSI template.
  Backend receives template only — never talks to hardware directly.
  Each SDK class: is_available(), capture(), get_device_info()
"""
import os
import abc
import time
import hmac
import hashlib
import json
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Provider config ───────────────────────────────────────────────────────
PROVIDER          = os.getenv("FINGERPRINT_PROVIDER", "DEMO").upper()
PORICHOY_BASE_URL = os.getenv("PORICHOY_BASE_URL", "https://api.porichoy.gov.bd/v1")
PORICHOY_API_KEY  = os.getenv("PORICHOY_API_KEY", "")
REQUEST_TIMEOUT   = int(os.getenv("FINGERPRINT_TIMEOUT", "30"))

# ── BFIU §3.2 limits ──────────────────────────────────────────────────────
MAX_ATTEMPTS_PER_SESSION = 10
MAX_SESSIONS_PER_DAY     = 2
FALLBACK_AFTER_SESSIONS  = 3

# ── In-memory fallback attempt counter ───────────────────────────────────
_session_attempts: dict = {}


# ══════════════════════════════════════════════════════════════════════════
# ABSTRACT SDK INTERFACE
# ══════════════════════════════════════════════════════════════════════════

class FingerprintSDKBase(abc.ABC):
    """
    Abstract base for all fingerprint scanner SDKs.
    Implement is_available(), capture(), get_device_info() per device.
    """
    PROVIDER_NAME: str = "BASE"
    SUPPORTED_MODELS: list = []

    @staticmethod
    @abc.abstractmethod
    def is_available() -> bool:
        """Return True if SDK library and hardware device are present."""

    @staticmethod
    @abc.abstractmethod
    def capture() -> Optional[str]:
        """
        Capture fingerprint from hardware.
        Returns Base64 WSQ or ISO/ANSI template string.
        Raises NotImplementedError if SDK not installed.
        """

    @classmethod
    def get_device_info(cls) -> dict:
        """Return device metadata."""
        return {
            "provider":         cls.PROVIDER_NAME,
            "supported_models": cls.SUPPORTED_MODELS,
            "available":        cls.is_available(),
        }


# ══════════════════════════════════════════════════════════════════════════
# MANTRA SDK — MFS100 / MFS500 / L1
# ══════════════════════════════════════════════════════════════════════════

class MantraScanner(FingerprintSDKBase):
    """
    Mantra MFS100 / MFS500 / L1 Fingerprint Scanner
    SDK: https://www.mantratec.com/products/Fingerprint-Sensor-Module/MFS100
    Windows DLL: MFS100.dll (32-bit), MFS100x64.dll (64-bit)
    Install: Download Mantra SDK from mantratec.com, place DLL in PATH
    API docs: https://www.mantratec.com/Developer-Zone
    """
    PROVIDER_NAME    = "MANTRA"
    SUPPORTED_MODELS = ["MFS100", "MFS500", "MFS100V54", "L1"]

    @staticmethod
    def is_available() -> bool:
        try:
            # Check for Mantra DLL or Python wrapper
            import ctypes
            ctypes.WinDLL("MFS100.dll")
            return True
        except Exception:
            return False

    @staticmethod
    def capture() -> Optional[str]:
        """
        Capture from Mantra MFS100/MFS500.
        Replace stub with actual SDK call when DLL is installed.

        SDK usage example:
            from mantra_mfs100 import MFS100
            mfs = MFS100()
            mfs.init_device()
            result = mfs.capture_fingerprint(timeout=10000)
            return result.iso_template_base64   # or result.wsq_base64
        """
        raise NotImplementedError(
            "Mantra SDK DLL not found. "
            "Download from https://www.mantratec.com/Developer-Zone "
            "or set FINGERPRINT_PROVIDER=DEMO"
        )

    @staticmethod
    def capture_with_quality_check() -> dict:
        """
        Capture with quality threshold check (NFIQ score).
        Returns template + quality score.
        """
        template = MantraScanner.capture()
        return {
            "template":   template,
            "quality":    0,   # populated by SDK
            "nfiq_score": 0,   # NIST Fingerprint Image Quality
            "device":     "MANTRA",
        }


# ══════════════════════════════════════════════════════════════════════════
# MORPHO SDK — MSO 1300 / MSO 1350 / MSO 300 / MSO Ultra
# ══════════════════════════════════════════════════════════════════════════

class MorphoScanner(FingerprintSDKBase):
    """
    Idemia (formerly Morpho/Sagem) MSO Series Fingerprint Scanner
    Models: MSO 1300, MSO 1350, MSO 300, MSO Ultra, MSO 1350 FIPS
    SDK: Morpho MSO SDK (MorphoSmart SDK)
    DLL: mso_sdk.dll / morpho_mso_sdk.dll
    Docs: https://www.idemia.com/biometric-sensors

    USB Protocol: MSO devices use libusb + Morpho proprietary protocol.
    Template format: ISO/IEC 19794-2 (minutiae) or WSQ image.
    """
    PROVIDER_NAME    = "MORPHO"
    SUPPORTED_MODELS = ["MSO1300", "MSO1350", "MSO300", "MSO_ULTRA", "MSO1350_FIPS"]

    @staticmethod
    def is_available() -> bool:
        try:
            import ctypes
            # Try Morpho MSO SDK DLL
            ctypes.WinDLL("mso_sdk.dll")
            return True
        except Exception:
            try:
                import ctypes
                ctypes.WinDLL("morpho_mso_sdk.dll")
                return True
            except Exception:
                return False

    @staticmethod
    def capture() -> Optional[str]:
        """
        Capture from Morpho MSO device.
        Replace with actual MorphoSmart SDK call.

        SDK usage example:
            from morpho_sdk import MorphoSmart
            mso = MorphoSmart()
            mso.open(port=0)               # open first USB device
            mso.set_latent_detect(False)
            result = mso.capture(timeout=15000)
            template = result.get_iso_template()
            return base64.b64encode(template).decode()
        """
        raise NotImplementedError(
            "Morpho MSO SDK not found. "
            "Download MorphoSmart SDK from https://www.idemia.com "
            "or set FINGERPRINT_PROVIDER=DEMO"
        )

    @staticmethod
    def get_connected_devices() -> list:
        """
        List all connected Morpho USB devices.
        Returns list of device info dicts.
        """
        # from morpho_sdk import MorphoSmart
        # return MorphoSmart.list_devices()
        return []

    @staticmethod
    def capture_dual_finger(finger1: str, finger2: str) -> dict:
        """
        Dual finger capture for MSO 1350 (two-finger platen).
        Returns two templates.
        """
        raise NotImplementedError("Morpho dual-finger capture requires MSO SDK")


# ══════════════════════════════════════════════════════════════════════════
# STARTEK SDK — FM220U / FM220 / EM500 / FM200
# ══════════════════════════════════════════════════════════════════════════

class StartekScanner(FingerprintSDKBase):
    """
    Startek Engineering FM220U / FM220 / EM500 / FM200
    SDK: Startek BioAPI SDK / SFRCapture SDK
    DLL: SFRCapture.dll / STCapture.dll
    Docs: https://www.startek.com/products/fingerprint-readers

    Note: FM220U is USB HID class device — no driver install required on Windows 10+.
    Template: ISO/IEC 19794-2 minutiae or raw image (500 DPI, 8-bit gray).
    """
    PROVIDER_NAME    = "STARTEK"
    SUPPORTED_MODELS = ["FM220U", "FM220", "EM500", "FM200", "FM300"]

    @staticmethod
    def is_available() -> bool:
        try:
            import ctypes
            ctypes.WinDLL("SFRCapture.dll")
            return True
        except Exception:
            try:
                import ctypes
                ctypes.WinDLL("STCapture.dll")
                return True
            except Exception:
                return False

    @staticmethod
    def capture() -> Optional[str]:
        """
        Capture from Startek FM220U/FM220/EM500.
        Replace with actual SFRCapture SDK call.

        SDK usage example:
            import ctypes
            sdk = ctypes.WinDLL("SFRCapture.dll")
            sdk.OpenDevice(0)              # open first device
            sdk.SetLED(1)                  # turn on LED
            buf = ctypes.create_string_buffer(4096)
            sdk.CaptureFinger(buf, 4096, 10000)   # timeout=10s
            import base64
            return base64.b64encode(buf.raw).decode()
        """
        raise NotImplementedError(
            "Startek SFRCapture SDK not found. "
            "Download from https://www.startek.com "
            "or set FINGERPRINT_PROVIDER=DEMO"
        )

    @staticmethod
    def get_device_serial() -> Optional[str]:
        """Return connected Startek device serial number."""
        # sdk.GetDeviceSerial(...)
        return None


# ══════════════════════════════════════════════════════════════════════════
# DIGITALPERSONA SDK — U.are.U 4500 / 5160 / 5300
# ══════════════════════════════════════════════════════════════════════════

class DigitalPersonaScanner(FingerprintSDKBase):
    """
    DigitalPersona (HID Global) U.are.U Series
    Models: U.are.U 4500, 5160, 5300
    SDK: DigitalPersona Fingerprint SDK (DPFJ)
    DLL: dpfj.dll
    Docs: https://www.hidglobal.com/products/readers/digitalpersona
    """
    PROVIDER_NAME    = "DIGITALPERSONA"
    SUPPORTED_MODELS = ["U.are.U 4500", "U.are.U 5160", "U.are.U 5300"]

    @staticmethod
    def is_available() -> bool:
        try:
            import ctypes
            ctypes.WinDLL("dpfj.dll")
            return True
        except Exception:
            return False

    @staticmethod
    def capture() -> Optional[str]:
        """
        Capture from DigitalPersona U.are.U.
        Replace with DPFJ SDK call.

        SDK usage example:
            from dpfj import FingerprintReader
            reader = FingerprintReader()
            reader.open()
            sample = reader.get_sample(timeout=10000)
            return sample.to_base64_fmd()   # Feature Minutiae Data
        """
        raise NotImplementedError(
            "DigitalPersona DPFJ SDK not found. "
            "Download from https://www.hidglobal.com "
            "or set FINGERPRINT_PROVIDER=DEMO"
        )


# ══════════════════════════════════════════════════════════════════════════
# HARDWARE PROVIDER REGISTRY
# ══════════════════════════════════════════════════════════════════════════

HARDWARE_PROVIDERS: dict[str, type[FingerprintSDKBase]] = {
    "MANTRA":          MantraScanner,
    "MORPHO":          MorphoScanner,
    "STARTEK":         StartekScanner,
    "DIGITALPERSONA":  DigitalPersonaScanner,
}


def get_available_providers() -> list[dict]:
    """Return list of all providers and their availability status."""
    providers = [{"provider": "DEMO", "available": True, "models": ["DEMO"]}]
    for name, cls in HARDWARE_PROVIDERS.items():
        providers.append(cls.get_device_info())
    return providers


def auto_detect_provider() -> Optional[str]:
    """
    Auto-detect first available hardware provider.
    Priority: MANTRA → MORPHO → STARTEK → DIGITALPERSONA → DEMO
    """
    for name in ["MANTRA", "MORPHO", "STARTEK", "DIGITALPERSONA"]:
        cls = HARDWARE_PROVIDERS[name]
        if cls.is_available():
            log.info("[M36] Auto-detected fingerprint provider: %s", name)
            return name
    log.info("[M36] No hardware detected — using DEMO provider")
    return "DEMO"


# ══════════════════════════════════════════════════════════════════════════
# DEMO PROVIDER
# ══════════════════════════════════════════════════════════════════════════

DEMO_SCENARIOS = {
    "MATCH":       {"matched": True,  "score": 87.3, "quality": 92},
    "NO_MATCH":    {"matched": False, "score": 12.1, "quality": 88},
    "LOW_QUALITY": {"matched": False, "score": 0.0,  "quality": 18},
    "TIMEOUT":     None,
}

_demo_scenario = "MATCH"


def set_demo_scenario(scenario: str) -> bool:
    global _demo_scenario
    if scenario not in DEMO_SCENARIOS:
        return False
    _demo_scenario = scenario
    return True


def get_demo_scenario() -> str:
    return _demo_scenario


def _verify_demo(nid_number: str, dob: str, finger_position: str) -> dict:
    time.sleep(0.1)
    if _demo_scenario == "TIMEOUT":
        raise TimeoutError("EC gateway timeout (DEMO)")
    s = DEMO_SCENARIOS[_demo_scenario]
    return {
        "matched":         s["matched"],
        "score":           s["score"],
        "quality":         s["quality"],
        "finger_position": finger_position,
        "provider":        "DEMO",
        "scenario":        _demo_scenario,
    }


# ══════════════════════════════════════════════════════════════════════════
# PORICHOY API PROVIDER
# ══════════════════════════════════════════════════════════════════════════

def _sign_porichoy_request(payload: bytes, timestamp: str) -> str:
    payload_hash = hashlib.sha256(payload).hexdigest()
    message      = f"{timestamp}.{payload_hash}".encode()
    return hmac.new(PORICHOY_API_KEY.encode(), message, hashlib.sha256).hexdigest()


def _verify_porichoy(nid_number: str, dob: str,
                     fingerprint_b64: str, finger_position: str) -> dict:
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx not installed. Run: pip install httpx")

    payload   = json.dumps({
        "nid": nid_number, "dob": dob,
        "fingerprint": fingerprint_b64, "finger": finger_position,
    }).encode()
    timestamp = str(int(time.time()))
    signature = _sign_porichoy_request(payload, timestamp)

    response = httpx.post(
        f"{PORICHOY_BASE_URL}/fingerprint/verify",
        content=payload,
        headers={
            "X-API-Key":    PORICHOY_API_KEY,
            "X-Timestamp":  timestamp,
            "X-Signature":  signature,
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "matched":         data.get("matched", False),
        "score":           float(data.get("score", 0)),
        "quality":         int(data.get("quality", 0)),
        "finger_position": finger_position,
        "provider":        "PORICHOY",
    }


# ══════════════════════════════════════════════════════════════════════════
# BFIU ATTEMPT TRACKING (Redis-backed with in-memory fallback)
# ══════════════════════════════════════════════════════════════════════════

def _check_limits(session_id: str) -> tuple:
    attempts = _get_attempts(session_id)
    if attempts >= MAX_ATTEMPTS_PER_SESSION:
        return False, f"Attempt limit reached ({MAX_ATTEMPTS_PER_SESSION}/session)."
    return True, ""


def _get_attempts(session_id: str) -> int:
    try:
        from app.services.redis_client import get_redis
        r = get_redis()
        if r:
            val = r.get(f"fp_att:{session_id}")
            return int(val) if val else 0
    except Exception:
        pass
    return _session_attempts.get(session_id, 0)


def _increment_attempt(session_id: str) -> int:
    try:
        from app.services.redis_client import get_redis
        r = get_redis()
        if r:
            key   = f"fp_att:{session_id}"
            count = r.incr(key)
            if count == 1:
                r.expire(key, 86400)
            return count
    except Exception:
        pass
    _session_attempts[session_id] = _session_attempts.get(session_id, 0) + 1
    return _session_attempts[session_id]


def _reset_session(session_id: str) -> None:
    try:
        from app.services.redis_client import get_redis
        r = get_redis()
        if r:
            r.delete(f"fp_att:{session_id}")
    except Exception:
        pass
    _session_attempts.pop(session_id, None)


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def verify_fingerprint(
    session_id:      str,
    nid_number:      str,
    dob:             str,
    fingerprint_b64: str,
    finger_position: str = "RIGHT_INDEX",
) -> dict:
    """
    Main fingerprint verification entry point.
    Routes to DEMO, PORICHOY, or hardware SDK based on FINGERPRINT_PROVIDER.
    Enforces BFIU §3.2 attempt limits via Redis.
    """
    start = time.time()

    # Resolve AUTO provider
    effective_provider = PROVIDER
    if effective_provider == "AUTO":
        effective_provider = auto_detect_provider()

    # BFIU attempt limit check
    allowed, reason = _check_limits(session_id)
    if not allowed:
        return {
            "session_id":       session_id,
            "verdict":          "LIMIT_EXCEEDED",
            "verdict_reason":   reason,
            "matched":          False,
            "score":            0.0,
            "attempt_number":   _get_attempts(session_id),
            "provider":         effective_provider,
            "processing_ms":    0,
            "bfiu_ref":         "BFIU Circular No. 29 — Section 3.2",
        }

    attempt = _increment_attempt(session_id)

    try:
        if effective_provider == "DEMO":
            result = _verify_demo(nid_number, dob, finger_position)

        elif effective_provider == "PORICHOY":
            if not PORICHOY_API_KEY:
                result = _verify_demo(nid_number, dob, finger_position)
                result["provider"] = "PORICHOY_DEMO_FALLBACK"
            else:
                result = _verify_porichoy(nid_number, dob, fingerprint_b64, finger_position)

        elif effective_provider in HARDWARE_PROVIDERS:
            cls = HARDWARE_PROVIDERS[effective_provider]
            if not cls.is_available():
                log.warning("[M36] %s SDK not available — falling back to DEMO", effective_provider)
                result = _verify_demo(nid_number, dob, finger_position)
                result["provider"] = f"{effective_provider}_DEMO_FALLBACK"
            else:
                if not fingerprint_b64:
                    fingerprint_b64 = cls.capture()
                result = _verify_porichoy(nid_number, dob, fingerprint_b64, finger_position)

        else:
            log.warning("[M36] Unknown provider %s — falling back to DEMO", effective_provider)
            result = _verify_demo(nid_number, dob, finger_position)

    except TimeoutError as exc:
        return {
            "session_id":     session_id,
            "verdict":        "PROVIDER_TIMEOUT",
            "verdict_reason": str(exc),
            "matched":        False,
            "score":          0.0,
            "attempt_number": attempt,
            "provider":       effective_provider,
            "processing_ms":  int((time.time() - start) * 1000),
            "bfiu_ref":       "BFIU Circular No. 29 — Section 3.2",
        }
    except Exception as exc:
        log.error("[M36] Fingerprint verify error: %s", exc)
        return {
            "session_id":     session_id,
            "verdict":        "PROVIDER_ERROR",
            "verdict_reason": str(exc),
            "matched":        False,
            "score":          0.0,
            "attempt_number": attempt,
            "provider":       effective_provider,
            "processing_ms":  int((time.time() - start) * 1000),
            "bfiu_ref":       "BFIU Circular No. 29 — Section 3.2",
        }

    # Verdict determination
    if result["matched"]:
        verdict, verdict_reason = "MATCHED", "Fingerprint biometric verified successfully"
    elif result.get("quality", 100) < 30:
        verdict = "LOW_QUALITY"
        verdict_reason = f"Fingerprint quality too low ({result.get('quality')}). Re-scan required."
    else:
        verdict, verdict_reason = "NO_MATCH", "Fingerprint does not match NID record"

    fallback_required = attempt >= FALLBACK_AFTER_SESSIONS and verdict != "MATCHED"

    return {
        "session_id":         session_id,
        "verdict":            verdict,
        "verdict_reason":     verdict_reason,
        "matched":            result["matched"],
        "score":              result["score"],
        "quality":            result.get("quality", 0),
        "finger_position":    result["finger_position"],
        "attempt_number":     attempt,
        "attempts_remaining": max(0, MAX_ATTEMPTS_PER_SESSION - attempt),
        "fallback_required":  fallback_required,
        "provider":           result["provider"],
        "processing_ms":      int((time.time() - start) * 1000),
        "bfiu_ref":           "BFIU Circular No. 29 — Section 3.2",
    }


def get_provider_status() -> dict:
    """Return status of all fingerprint providers."""
    effective = PROVIDER if PROVIDER != "AUTO" else auto_detect_provider()
    return {
        "configured_provider": PROVIDER,
        "effective_provider":  effective,
        "providers":           get_available_providers(),
        "demo_scenario":       get_demo_scenario(),
        "bfiu_limits": {
            "max_attempts_per_session": MAX_ATTEMPTS_PER_SESSION,
            "max_sessions_per_day":     MAX_SESSIONS_PER_DAY,
            "fallback_after_attempts":  FALLBACK_AFTER_SESSIONS,
        },
    }
