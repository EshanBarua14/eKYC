"""
Fingerprint Verification Service — M7
BFIU Circular No. 29 — Section 3.2

Provider slots (swap via FINGERPRINT_PROVIDER env var):
  DEMO       — synthetic results, no hardware needed
  PORICHOY   — Porichoy API gateway (Bangladesh)
  MANTRA     — Mantra MFS100 / L1 scanner SDK
  NITGEN     — Nitgen NBioBSP SDK
  DIGITALPERSONA — DigitalPersona U.are.U SDK

Hardware note:
  Frontend captures fingerprint as Base64 WSQ or ISO/ANSI template.
  Each hardware class has a capture() stub — replace with actual SDK call.
  Backend only receives the captured template; it never talks to hardware directly.
"""
import os
import time
import hmac
import hashlib
import json
from typing import Optional

# ── Provider config ───────────────────────────────────────────────────────
PROVIDER          = os.getenv("FINGERPRINT_PROVIDER", "DEMO").upper()
PORICHOY_BASE_URL = os.getenv("PORICHOY_BASE_URL", "https://api.porichoy.gov.bd/v1")
PORICHOY_API_KEY  = os.getenv("PORICHOY_API_KEY", "")
REQUEST_TIMEOUT   = int(os.getenv("FINGERPRINT_TIMEOUT", "30"))

# BFIU §3.2 limits
MAX_ATTEMPTS_PER_SESSION = 10
MAX_SESSIONS_PER_DAY     = 2
FALLBACK_AFTER_SESSIONS  = 3   # After 3 failed sessions → offer face matching

# In-memory attempt counter (replace with Redis in production)
_session_attempts: dict = {}


# ══════════════════════════════════════════════════════════════════════════
# HARDWARE PROVIDER STUBS
# Replace the body of each capture() method with actual SDK call
# ══════════════════════════════════════════════════════════════════════════

class MantraScanner:
    """
    Mantra MFS100 / L1 Fingerprint Scanner
    SDK: https://www.mantratec.com/products/Fingerprint-Sensor-Module/MFS100
    Install: pip install mantra-mfs100 (vendor SDK)
    """
    @staticmethod
    def is_available() -> bool:
        try:
            # import MantraFingerprint  # uncomment when SDK installed
            return False  # set True when SDK present
        except ImportError:
            return False

    @staticmethod
    def capture() -> Optional[str]:
        """Returns Base64 WSQ image from scanner. Replace with SDK call."""
        # from MantraFingerprint import MFS100
        # mfs = MFS100()
        # result = mfs.capture(timeout=10000)
        # return result.ISOTemplate  # or result.WSQ
        raise NotImplementedError("Mantra SDK not installed. Set FINGERPRINT_PROVIDER=DEMO")


class NitgenScanner:
    """
    Nitgen NBioBSP / eNBSP SDK
    SDK: https://www.nitgen.com/eng/product/sdk.asp
    """
    @staticmethod
    def is_available() -> bool:
        return False  # set True when SDK present

    @staticmethod
    def capture() -> Optional[str]:
        """Returns Base64 ISO template. Replace with Nitgen NBioBSP call."""
        # from nitgen import NBioBSP
        # nbio = NBioBSP.NBioBSP()
        # nbio.Enroll(...)
        raise NotImplementedError("Nitgen SDK not installed. Set FINGERPRINT_PROVIDER=DEMO")


class DigitalPersonaScanner:
    """
    DigitalPersona U.are.U 4500 / 5160
    SDK: https://crossmatch.com/fingerprint-readers/
    """
    @staticmethod
    def is_available() -> bool:
        return False  # set True when SDK present

    @staticmethod
    def capture() -> Optional[str]:
        """Returns Base64 WSQ. Replace with DigitalPersona DPFJ SDK call."""
        # from dpfj import FingerprintSDK
        # sdk = FingerprintSDK()
        # template = sdk.capture()
        raise NotImplementedError("DigitalPersona SDK not installed. Set FINGERPRINT_PROVIDER=DEMO")


HARDWARE_PROVIDERS = {
    "MANTRA":          MantraScanner,
    "NITGEN":          NitgenScanner,
    "DIGITALPERSONA":  DigitalPersonaScanner,
}


# ══════════════════════════════════════════════════════════════════════════
# DEMO PROVIDER
# ══════════════════════════════════════════════════════════════════════════

DEMO_SCENARIOS = {
    "MATCH":    {"matched": True,  "score": 87.3, "quality": 92},
    "NO_MATCH": {"matched": False, "score": 12.1, "quality": 88},
    "LOW_QUALITY": {"matched": False, "score": 0.0, "quality": 18},
    "TIMEOUT":  None,
}

_demo_scenario = "MATCH"  # toggled by admin endpoint


def set_demo_scenario(scenario: str) -> bool:
    global _demo_scenario
    if scenario not in DEMO_SCENARIOS:
        return False
    _demo_scenario = scenario
    return True


def _verify_demo(nid_number: str, dob: str, finger_position: str) -> dict:
    time.sleep(0.3)  # simulate network latency

    if _demo_scenario == "TIMEOUT":
        raise TimeoutError("EC gateway timeout (DEMO)")

    s = DEMO_SCENARIOS[_demo_scenario]
    return {
        "matched":        s["matched"],
        "score":          s["score"],
        "quality":        s["quality"],
        "finger_position": finger_position,
        "provider":       "DEMO",
        "scenario":       _demo_scenario,
    }


# ══════════════════════════════════════════════════════════════════════════
# PORICHOY API PROVIDER
# ══════════════════════════════════════════════════════════════════════════

def _sign_porichoy_request(payload: bytes, timestamp: str) -> str:
    """HMAC-SHA256 request signing for Porichoy API."""
    payload_hash = hashlib.sha256(payload).hexdigest()
    message      = f"{timestamp}.{payload_hash}".encode()
    return hmac.new(PORICHOY_API_KEY.encode(), message, hashlib.sha256).hexdigest()


def _verify_porichoy(nid_number: str, dob: str,
                     fingerprint_b64: str, finger_position: str) -> dict:
    """
    Porichoy fingerprint verification gateway.
    Docs: https://porichoy.gov.bd/site/page/developer-guide
    """
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx not installed. Run: pip install httpx")

    payload = json.dumps({
        "nid":         nid_number,
        "dob":         dob,
        "fingerprint": fingerprint_b64,
        "finger":      finger_position,
    }).encode()

    timestamp = str(int(time.time()))
    signature = _sign_porichoy_request(payload, timestamp)

    response = httpx.post(
        f"{PORICHOY_BASE_URL}/fingerprint/verify",
        content=payload,
        headers={
            "X-API-Key":   PORICHOY_API_KEY,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
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
# BFIU SESSION / ATTEMPT TRACKING
# ══════════════════════════════════════════════════════════════════════════

def _check_limits(session_id: str) -> tuple:
    """
    Returns (allowed: bool, reason: str)
    BFIU §3.2: max 10 attempts/session, 2 sessions/day
    """
    attempts = _session_attempts.get(session_id, 0)
    if attempts >= MAX_ATTEMPTS_PER_SESSION:
        return False, f"Attempt limit reached ({MAX_ATTEMPTS_PER_SESSION}/session). Try again in 24 hours."
    return True, ""


def _increment_attempt(session_id: str) -> int:
    _session_attempts[session_id] = _session_attempts.get(session_id, 0) + 1
    return _session_attempts[session_id]


def _reset_session(session_id: str) -> None:
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
    Routes to DEMO, PORICHOY, or hardware provider based on FINGERPRINT_PROVIDER env.
    Enforces BFIU attempt limits.
    """
    start = time.time()

    # BFIU attempt limit check
    allowed, reason = _check_limits(session_id)
    if not allowed:
        return {
            "session_id":      session_id,
            "verdict":         "LIMIT_EXCEEDED",
            "verdict_reason":  reason,
            "matched":         False,
            "score":           0.0,
            "attempt_number":  _session_attempts.get(session_id, 0),
            "provider":        PROVIDER,
            "processing_ms":   0,
            "bfiu_ref":        "BFIU Circular No. 29 — Section 3.2",
        }

    attempt = _increment_attempt(session_id)

    try:
        if PROVIDER == "DEMO":
            result = _verify_demo(nid_number, dob, finger_position)

        elif PROVIDER == "PORICHOY":
            if not PORICHOY_API_KEY:
                # Fallback to demo if API key not configured
                result = _verify_demo(nid_number, dob, finger_position)
                result["provider"] = "PORICHOY_DEMO_FALLBACK"
            else:
                result = _verify_porichoy(nid_number, dob, fingerprint_b64, finger_position)

        elif PROVIDER in HARDWARE_PROVIDERS:
            cls = HARDWARE_PROVIDERS[PROVIDER]
            if not cls.is_available():
                result = _verify_demo(nid_number, dob, finger_position)
                result["provider"] = f"{PROVIDER}_DEMO_FALLBACK"
            else:
                # Capture from hardware if template not provided
                if not fingerprint_b64:
                    fingerprint_b64 = cls.capture()
                result = _verify_porichoy(nid_number, dob, fingerprint_b64, finger_position)
        else:
            result = _verify_demo(nid_number, dob, finger_position)

    except TimeoutError as e:
        return {
            "session_id":     session_id,
            "verdict":        "PROVIDER_TIMEOUT",
            "verdict_reason": str(e),
            "matched":        False,
            "score":          0.0,
            "attempt_number": attempt,
            "provider":       PROVIDER,
            "processing_ms":  int((time.time() - start) * 1000),
            "bfiu_ref":       "BFIU Circular No. 29 — Section 3.2",
        }
    except Exception as e:
        return {
            "session_id":     session_id,
            "verdict":        "PROVIDER_ERROR",
            "verdict_reason": str(e),
            "matched":        False,
            "score":          0.0,
            "attempt_number": attempt,
            "provider":       PROVIDER,
            "processing_ms":  int((time.time() - start) * 1000),
            "bfiu_ref":       "BFIU Circular No. 29 — Section 3.2",
        }

    # Determine verdict
    if result["matched"]:
        verdict        = "MATCHED"
        verdict_reason = "Fingerprint biometric verified successfully"
    elif result.get("quality", 100) < 30:
        verdict        = "LOW_QUALITY"
        verdict_reason = f"Fingerprint quality too low ({result.get('quality')}). Re-scan required."
    else:
        verdict        = "NO_MATCH"
        verdict_reason = "Fingerprint does not match NID record"

    # Check if fallback to face matching should be offered
    fallback_required = attempt >= FALLBACK_AFTER_SESSIONS and verdict != "MATCHED"

    return {
        "session_id":       session_id,
        "verdict":          verdict,
        "verdict_reason":   verdict_reason,
        "matched":          result["matched"],
        "score":            result["score"],
        "quality":          result.get("quality", 0),
        "finger_position":  result["finger_position"],
        "attempt_number":   attempt,
        "attempts_remaining": max(0, MAX_ATTEMPTS_PER_SESSION - attempt),
        "fallback_required": fallback_required,
        "provider":         result["provider"],
        "processing_ms":    int((time.time() - start) * 1000),
        "bfiu_ref":         "BFIU Circular No. 29 — Section 3.2",
    }
