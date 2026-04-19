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

# ── Client mode ───────────────────────────────────────────────────────────
NID_API_MODE     = "DEMO"   # LIVE | DEMO | STUB
NID_API_BASE_URL = "https://nid.ec.gov.bd/api/v1"

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
    effective_mode = mode or NID_API_MODE

    if effective_mode == "LIVE":
        return _live_lookup(nid_number)
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


def _live_lookup(nid_number: str) -> dict:
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

        headers = {
            "Authorization": f"Bearer {settings.SECRET_KEY}",
            "Content-Type":  "application/json",
            "X-Institution": "XPERT_FINTECH",
        }
        resp = session.post(
            f"{NID_API_BASE_URL}/verify",
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
