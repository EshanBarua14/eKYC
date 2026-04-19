"""
Session/Attempt Limiter — M41 Redis upgrade
Redis backend with automatic in-memory fallback for dev/CI.
BFIU Circular No. 29 Section 3.2 and 3.3.
All public function signatures unchanged from M28.
"""
import hmac
import hashlib
import time
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from app.core.config import settings
from app.services.redis_client import get_redis

log = logging.getLogger(__name__)

# ── NID hashing ───────────────────────────────────────────────────────────
_INSTITUTION_SECRET = settings.SECRET_KEY.encode()

def hash_nid(nid_number: str) -> str:
    """HMAC-SHA256(nid_number + institution_secret). Never stored in plaintext."""
    return hmac.new(
        _INSTITUTION_SECRET,
        nid_number.strip().encode(),
        hashlib.sha256
    ).hexdigest()


# ── In-memory fallback store ──────────────────────────────────────────────
_sessions: dict = {}
_attempts: dict = {}

MAX_ATTEMPTS_PER_SESSION = settings.BFIU_MAX_ATTEMPTS_PER_SESSION   # 10
MAX_SESSIONS_PER_DAY     = settings.BFIU_MAX_SESSIONS_PER_DAY       # 2

# ── Key helpers ───────────────────────────────────────────────────────────
def _session_key(nid_hash: str) -> str:
    today = date.today().isoformat()
    return f"sess:{nid_hash}:{today}"

def _attempt_key(session_key: str) -> str:
    return f"att:{session_key}"


# ── Session counting ──────────────────────────────────────────────────────
def get_session_count_today(nid_hash: str) -> int:
    """Return number of sessions started today for this NID hash."""
    r = get_redis()
    if r is not None:
        try:
            val = r.get(_session_key(nid_hash))
            return int(val) if val else 0
        except Exception as exc:
            log.warning("[M41] session_count Redis error: %s", exc)
    today = date.today().isoformat()
    return _sessions.get(nid_hash, {}).get(today, 0)


def increment_session_count(nid_hash: str) -> int:
    """Increment session count for today. Returns new count."""
    r = get_redis()
    if r is not None:
        try:
            key = _session_key(nid_hash)
            count = r.incr(key)
            if count == 1:
                # Expire at next midnight UTC
                now = datetime.now(timezone.utc)
                midnight = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                ttl = int((midnight - now).total_seconds())
                r.expire(key, ttl)
            return count
        except Exception as exc:
            log.warning("[M41] increment_session Redis error: %s", exc)

    today = date.today().isoformat()
    if nid_hash not in _sessions:
        _sessions[nid_hash] = {}
    _sessions[nid_hash][today] = _sessions[nid_hash].get(today, 0) + 1
    return _sessions[nid_hash][today]


def check_session_limit(nid_hash: str) -> dict:
    """Check if NID can start a new session today."""
    count = get_session_count_today(nid_hash)
    return {
        "allowed":       count < MAX_SESSIONS_PER_DAY,
        "current_count": count,
        "max_count":     MAX_SESSIONS_PER_DAY,
        "retry_after":   _next_midnight_iso() if count >= MAX_SESSIONS_PER_DAY else None,
    }


# ── Attempt counting ──────────────────────────────────────────────────────
def get_attempt_count(session_key: str) -> int:
    """Return number of attempts for this session key."""
    r = get_redis()
    if r is not None:
        try:
            val = r.get(_attempt_key(session_key))
            return int(val) if val else 0
        except Exception as exc:
            log.warning("[M41] attempt_count Redis error: %s", exc)
    return _attempts.get(session_key, 0)


def increment_attempt_count(session_key: str) -> int:
    """Increment attempt count. Returns new count."""
    r = get_redis()
    if r is not None:
        try:
            key = _attempt_key(session_key)
            count = r.incr(key)
            if count == 1:
                r.expire(key, 86400)   # 24hr TTL
            return count
        except Exception as exc:
            log.warning("[M41] increment_attempt Redis error: %s", exc)

    _attempts[session_key] = _attempts.get(session_key, 0) + 1
    return _attempts[session_key]


def check_attempt_limit(session_key: str) -> dict:
    """Check if session can make another attempt."""
    count = get_attempt_count(session_key)
    return {
        "allowed":       count < MAX_ATTEMPTS_PER_SESSION,
        "current_count": count,
        "max_count":     MAX_ATTEMPTS_PER_SESSION,
    }


def reset_session(session_key: str) -> None:
    """Reset attempt counter for a session (for testing)."""
    r = get_redis()
    if r is not None:
        try:
            r.delete(_attempt_key(session_key))
        except Exception:
            pass
    _attempts.pop(session_key, None)


def reset_nid_sessions(nid_hash: str) -> None:
    """Reset session counter for an NID hash (for testing)."""
    r = get_redis()
    if r is not None:
        try:
            r.delete(_session_key(nid_hash))
        except Exception:
            pass
    _sessions.pop(nid_hash, None)


# ── Helper ────────────────────────────────────────────────────────────────
def _next_midnight_iso() -> str:
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return midnight.isoformat()


# ── Combined gate ─────────────────────────────────────────────────────────
def gate_attempt(nid_number: str, session_key: str) -> dict:
    """
    Full BFIU gate check:
    1. Check session limit for NID (max 2/day)
    2. Check attempt limit for session (max 10)
    """
    nid_hash = hash_nid(nid_number)

    session_check = check_session_limit(nid_hash)
    if not session_check["allowed"]:
        return {
            "allowed": False,
            "reason":  "SESSION_LIMIT_EXCEEDED",
            "details": session_check,
        }

    attempt_check = check_attempt_limit(session_key)
    if not attempt_check["allowed"]:
        return {
            "allowed": False,
            "reason":  "ATTEMPT_LIMIT_EXCEEDED",
            "details": attempt_check,
        }

    return {
        "allowed": True,
        "reason":  None,
        "details": {
            "session_count": session_check["current_count"],
            "attempt_count": attempt_check["current_count"],
        },
    }
