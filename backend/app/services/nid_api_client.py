"""
Xpert Fintech eKYC Platform
EC NID API Client — M34
HTTP client with retry/backoff, pending_verification state,
Celery retry queue (max 6hrs, exponential backoff).
Modes: LIVE | DEMO | STUB
"""
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings

log = logging.getLogger(__name__)

# ── Client mode (reads from platform_settings.json at runtime) ───────────
def _get_nid_settings():
    import json, os
    sf = os.path.join(os.path.dirname(__file__), "../../platform_settings.json")
    try:
        with open(sf, "r", encoding="utf-8") as f:
            s = json.load(f)
        mode       = s.get("nid_api_mode", "DEMO")
        base_url   = s.get("nid_api_base_url", "https://nid.ec.gov.bd/api/v1")
        api_key    = s.get("nid_api_key", "")
        api_secret = s.get("nid_api_secret", "")
        client_id  = s.get("nid_api_client_id", "")
        return mode, base_url, api_key, api_secret, client_id
    except Exception:
        return "DEMO", "https://nid.ec.gov.bd/api/v1", "", "", ""

NID_API_MODE     = "DEMO"   # fallback default — overridden at runtime
NID_API_BASE_URL = "https://nid.ec.gov.bd/api/v1"

# ── FAKE_EC bearer token cache ────────────────────────────────────────────
_fake_ec_token: dict = {"token": None, "exp": 0}

# ── Retry config ──────────────────────────────────────────────────────────
MAX_SYNC_RETRIES  = 3       # retries within a single request
SYNC_RETRY_DELAY  = 1.0     # seconds between sync retries
REQUEST_TIMEOUT   = 10      # seconds

# ── EC error codes ────────────────────────────────────────────────────────
EC_UNAVAILABLE    = "EC_UNAVAILABLE"
EC_RATE_LIMITED   = "EC_RATE_LIMITED"
EC_AUTH_ERROR     = "EC_AUTH_ERROR"
EC_NOT_FOUND      = "EC_NOT_FOUND"
EC_SERVER_ERROR   = "EC_SERVER_ERROR"

# ── Demo NID database ─────────────────────────────────────────────────────
_DEMO_NID_DB = {
    # ── Real test NIDs for demo verification ─────────────────────────────
    "2375411929": {
        "nid_number":      "2375411929",
        "full_name_en":    "ESHAN BARUA",
        "full_name_bn":    "ঈশান বড়ুয়া",
        "date_of_birth":   "1994-08-14",
        "fathers_name":    "PRODIP BARUA",
        "fathers_name_bn": "প্রদীপ বড়ুয়া",
        "mothers_name":    "SHIMA BARUA",
        "mothers_name_bn": "সীমা বড়ুয়া",
        "present_address": "বাসা/হোল্ডিং: ৯৭, সবুজবাগ, রাজারবাগ, ঢাকা দক্ষিণ সিটি কর্পোরেশন, ঢাকা",
        "place_of_birth":  "DHAKA",
        "blood_group":     "O+",
        "gender":          "M",
        "issue_date":      "2016-08-30",
        "smart_card_no":   "BGD2375411929",
        "photo_url":       None,
    },
    "19858524905063671": {
        "nid_number":      "19858524905063671",
        "full_name_en":    "MD ABUL MOSHAD CHOWDHURY",
        "full_name_bn":    "মোঃ আবুল মোশাদ চৌধুরী",
        "date_of_birth":   "1985-03-03",
        "fathers_name":    "MD ABUL MASUD CHOWDHURY",
        "fathers_name_bn": "মোঃ আবুল মাসুদ চৌধুরী",
        "mothers_name":    "JANI CHOWDHURY",
        "mothers_name_bn": "জানী চৌধুরী",
        "present_address": "বাসা/হোল্ডিং: ৭৫, গোমস্তা পাড়া, ডাকঘর: রংপুর-৫৪০০, রংপুর সদর, রংপুর সিটি কর্পোরেশন, রংপুর",
        "place_of_birth":  "RANGPUR",
        "blood_group":     None,
        "gender":          "M",
        "issue_date":      "2016-05-10",
        "smart_card_no":   None,
        "photo_url":       None,
    },
    "1234567890123": {
        "nid_number":      "1234567890123",
        "full_name_en":    "RAHMAN HOSSAIN CHOWDHURY",
        "full_name_bn":    "রহমান হোসেন চৌধুরী",
        "date_of_birth":   "1990-01-15",
        "fathers_name":    "ABDUR RAHMAN CHOWDHURY",
        "mothers_name":    "MST RASHIDA BEGUM",
        "present_address": "123 Agrabad, Chittagong",
        "blood_group":     "O+",
        "gender":          "M",
        "photo_url":       None,
    },
    "9876543210987": {
        "nid_number":      "9876543210987",
        "full_name_en":    "FATEMA BEGUM",
        "full_name_bn":    "ফাতেমা বেগম",
        "date_of_birth":   "1985-06-20",
        "fathers_name":    "MD IBRAHIM",
        "mothers_name":    "MST AMENA KHATUN",
        "present_address": "456 Dhanmondi, Dhaka",
        "blood_group":     "A+",
        "gender":          "F",
        "photo_url":       None,
    },
    "1111111111111": {
        "nid_number":      "1111111111111",
        "full_name_en":    "KARIM UDDIN AHMED",
        "full_name_bn":    "করিম উদ্দিন আহমেদ",
        "date_of_birth":   "1975-03-10",
        "fathers_name":    "RAHIM UDDIN AHMED",
        "mothers_name":    "SUFIA BEGUM",
        "present_address": "789 Sylhet Sadar",
        "blood_group":     "B+",
        "gender":          "M",
        "photo_url":       None,
    },
}


# ── Public API ────────────────────────────────────────────────────────────
def lookup_nid(nid_number: str, mode: str = None) -> dict:
    """
    Look up NID in EC database.
    Returns structured result with found, data, source, and status fields.
    status: verified | not_found | pending_verification | ec_error
    """
    nid_number = nid_number.strip()
    runtime_mode, runtime_url, runtime_key, runtime_secret, runtime_client_id = _get_nid_settings()
    effective_mode = mode or runtime_mode

    if effective_mode == "LIVE":
        return _live_lookup(nid_number, runtime_url, runtime_key, runtime_secret)
    elif effective_mode == "FAKE_EC":
        return _fake_ec_lookup(nid_number, runtime_url, runtime_client_id, runtime_key)
    elif effective_mode == "DEMO":
        return _demo_lookup(nid_number)
    else:
        return _stub_lookup(nid_number)


def lookup_nid_with_retry(
    nid_number: str,
    session_id: str,
    institution_id: str = "default",
    enqueue_on_failure: bool = True,
) -> dict:
    """
    Lookup NID with sync retries. On EC unavailability:
    - Returns pending_verification state immediately
    - Enqueues Celery async retry task (max 6hrs exponential backoff)
    """
    nid_number = nid_number.strip()

    for attempt in range(1, MAX_SYNC_RETRIES + 1):
        result = lookup_nid(nid_number)
        status = result.get("status") or ("verified" if result.get("found") else "not_found")

        if status not in (EC_UNAVAILABLE, "ec_error") and result.get("found") is not False or result.get("found") is True:
            log.info("[M34] NID lookup success: nid=***%s attempt=%d", nid_number[-4:], attempt)
            result["status"] = "verified" if result.get("found") else "not_found"
            return result

        if result.get("error_code") == EC_UNAVAILABLE or result.get("status") == EC_UNAVAILABLE:
            log.warning("[M34] EC unavailable on attempt %d/%d", attempt, MAX_SYNC_RETRIES)
            if attempt < MAX_SYNC_RETRIES:
                time.sleep(SYNC_RETRY_DELAY * attempt)
            continue

        # Non-retryable error
        result["status"] = "not_found"
        return result

    # All sync retries exhausted — enqueue async Celery retry
    log.error("[M34] EC unavailable after %d attempts — queuing async retry: session=%s",
              MAX_SYNC_RETRIES, session_id)

    if enqueue_on_failure:
        _enqueue_async_retry(nid_number, session_id, institution_id)

    return {
        "found":       False,
        "status":      "pending_verification",
        "source":      NID_API_MODE,
        "nid_number":  nid_number,
        "session_id":  session_id,
        "error_code":  EC_UNAVAILABLE,
        "reason":      "EC API unavailable — queued for async retry (max 6hrs)",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }


def _enqueue_async_retry(nid_number: str, session_id: str, institution_id: str) -> None:
    """Enqueue Celery async NID verification retry."""
    try:
        from app.worker.tasks.nid_verify import verify_nid_async
        verify_nid_async.apply_async(
            args=[nid_number, session_id, institution_id],
            countdown=60,   # start after 1 min
        )
        log.info("[M34] Celery retry enqueued: session=%s", session_id)
    except Exception as exc:
        log.error("[M34] Failed to enqueue Celery retry: %s", exc)


# ── Backend implementations ───────────────────────────────────────────────
def _demo_lookup(nid_number: str) -> dict:
    """Return mock NID data from in-memory demo DB."""
    record = _DEMO_NID_DB.get(nid_number)
    if record:
        return {
            "found":      True,
            "status":     "verified",
            "source":     "DEMO",
            "nid_number": nid_number,
            "data":       record,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
    return {
        "found":      False,
        "status":     "not_found",
        "source":     "DEMO",
        "nid_number": nid_number,
        "data":       None,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "reason":     "NID not found in demo database",
    }


def _stub_lookup(nid_number: str) -> dict:
    """Offline stub — always returns a synthetic record."""
    return {
        "found":      True,
        "status":     "verified",
        "source":     "STUB",
        "nid_number": nid_number,
        "data": {
            "nid_number":    nid_number,
            "full_name_en":  "STUB CITIZEN",
            "full_name_bn":  "স্টাব নাগরিক",
            "date_of_birth": "2000-01-01",
            "gender":        "M",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _fake_ec_get_token(base_url: str, client_id: str, client_secret: str) -> str | None:
    """
    Authenticate against the fake EC API and return Bearer token.
    Caches token until expiry.
    """
    import requests, time as _time
    now = _time.time()
    cached = _fake_ec_token
    if cached["token"] and cached["exp"] > now + 60:
        return cached["token"]
    try:
        resp = requests.post(
            f"{base_url}/auth",
            json={"client_id": client_id, "client_secret": client_secret},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            cached["token"] = data["access_token"]
            cached["exp"]   = now + data.get("expires_in", 3600)
            log.info("[M34-FAKE-EC] Token obtained for client_id=%s", client_id)
            return cached["token"]
        log.error("[M34-FAKE-EC] Auth failed: %s %s", resp.status_code, resp.text[:200])
        return None
    except Exception as exc:
        log.error("[M34-FAKE-EC] Auth error: %s", exc)
        return None


def _fake_ec_lookup(
    nid_number: str,
    base_url: str = "http://localhost:8001/api/v1",
    client_id: str = "inst_xpert_001",
    client_secret: str = "sk_test_xpert_ekyc_secret_2026",
) -> dict:
    """
    Call the local fake EC API service.
    Acts exactly like _live_lookup but points to localhost:8001.
    Falls back to DEMO mode if fake EC service is unreachable.
    """
    import requests
    try:
        token = _fake_ec_get_token(base_url, client_id, client_secret)
        if not token:
            log.warning("[M34-FAKE-EC] No token — falling back to DEMO")
            return _demo_lookup(nid_number)

        resp = requests.post(
            f"{base_url}/verify",
            json={"nid_number": nid_number},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 200:
            data = resp.json()
            return {
                "found":      True,
                "status":     "verified",
                "source":     "FAKE_EC",
                "nid_number": nid_number,
                "data":       data.get("data", {}),
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 404:
            return {
                "found":      False,
                "status":     "not_found",
                "source":     "FAKE_EC",
                "error_code": EC_NOT_FOUND,
                "reason":     "NID not found in EC database",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 403:
            err = resp.json().get("detail", {})
            return {
                "found":      False,
                "status":     "ec_error",
                "source":     "FAKE_EC",
                "error_code": err.get("error_code", "NID_BLOCKED"),
                "reason":     err.get("message", "NID blocked"),
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 422:
            err = resp.json().get("detail", {})
            return {
                "found":      False,
                "status":     "ec_error",
                "source":     "FAKE_EC",
                "error_code": "INVALID_NID_FORMAT",
                "reason":     err.get("message", "Invalid NID format"),
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 429:
            return {
                "found":      False,
                "status":     EC_UNAVAILABLE,
                "source":     "FAKE_EC",
                "error_code": EC_RATE_LIMITED,
                "reason":     "EC API rate limited",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 401:
            # Token expired — clear cache and signal retry
            _fake_ec_token["token"] = None
            return {
                "found":      False,
                "status":     "ec_error",
                "source":     "FAKE_EC",
                "error_code": EC_AUTH_ERROR,
                "reason":     "EC API authentication failed",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "found":      False,
                "status":     EC_UNAVAILABLE,
                "source":     "FAKE_EC",
                "error_code": EC_SERVER_ERROR,
                "reason":     f"EC API returned {resp.status_code}",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }

    except Exception as exc:
        log.warning("[M34-FAKE-EC] Connection failed: %s — falling back to DEMO", exc)
        # Graceful fallback to DEMO if fake EC service is down
        result = _demo_lookup(nid_number)
        result["source"] = "DEMO_FALLBACK"
        return result


def _live_lookup(nid_number: str, base_url: str = None, api_key: str = None, api_secret: str = None) -> dict:
    """
    Live EC NID API call with timeout handling.
    Returns EC_UNAVAILABLE on connection failure for Celery retry queue.
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        _key = api_key or settings.SECRET_KEY
        _url = base_url or NID_API_BASE_URL
        headers = {
            "Authorization": f"Bearer {_key}",
            "Content-Type":  "application/json",
            "X-Institution": "XPERT_FINTECH",
        }
        resp = session.post(
            f"{_url}/verify",
            json={"nid_number": nid_number},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 200:
            data = resp.json()
            return {
                "found":      True,
                "status":     "verified",
                "source":     "LIVE",
                "nid_number": nid_number,
                "data":       data,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 404:
            return {
                "found":      False,
                "status":     "not_found",
                "source":     "LIVE",
                "error_code": EC_NOT_FOUND,
                "reason":     "NID not found in EC database",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 429:
            return {
                "found":      False,
                "status":     EC_UNAVAILABLE,
                "source":     "LIVE",
                "error_code": EC_RATE_LIMITED,
                "reason":     "EC API rate limit exceeded",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        elif resp.status_code == 401:
            return {
                "found":      False,
                "status":     "ec_error",
                "source":     "LIVE",
                "error_code": EC_AUTH_ERROR,
                "reason":     "EC API authentication failed",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "found":      False,
                "status":     EC_UNAVAILABLE,
                "source":     "LIVE",
                "error_code": EC_SERVER_ERROR,
                "reason":     f"EC API returned {resp.status_code}",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }

    except Exception as exc:
        log.warning("[M34] EC API connection error: %s", exc)
        return {
            "found":      False,
            "status":     EC_UNAVAILABLE,
            "source":     "LIVE",
            "error_code": EC_UNAVAILABLE,
            "reason":     str(exc),
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }


# ── Cross-match ───────────────────────────────────────────────────────────
def cross_match_nid(ocr_fields: dict, ec_record: dict) -> dict:
    """
    Compare OCR-extracted fields against EC database record.
    Returns match score and field-by-field result.
    """
    if not ec_record:
        return {"match": False, "score": 0, "reason": "No EC record to compare"}

    checks = {}
    score  = 0
    total  = 0

    ocr_name = (ocr_fields.get("full_name_en") or "").upper().strip()
    ec_name  = (ec_record.get("full_name_en")  or "").upper().strip()
    if ocr_name and ec_name:
        total += 1
        name_match = _fuzzy_name_match(ocr_name, ec_name)
        checks["name"] = name_match
        if name_match["matched"]:
            score += 1

    ocr_dob = (ocr_fields.get("date_of_birth") or "").strip()
    ec_dob  = (ec_record.get("date_of_birth")  or "").strip()
    if ocr_dob and ec_dob:
        total += 1
        dob_match = ocr_dob == ec_dob
        checks["dob"] = {"matched": dob_match, "ocr": ocr_dob, "ec": ec_dob}
        if dob_match:
            score += 1

    match_pct = (score / total * 100) if total > 0 else 0
    return {
        "match":          match_pct >= 50,
        "score_pct":      round(match_pct, 1),
        "checks":         checks,
        "fields_checked": total,
    }


def _fuzzy_name_match(name1: str, name2: str) -> dict:
    """Simple name matching with token overlap."""
    tokens1 = set(name1.split())
    tokens2 = set(name2.split())
    overlap  = tokens1 & tokens2
    union    = tokens1 | tokens2
    score    = len(overlap) / len(union) if union else 0
    return {
        "matched": score >= 0.5,
        "score":   round(score, 2),
        "ocr":     name1,
        "ec":      name2,
    }
