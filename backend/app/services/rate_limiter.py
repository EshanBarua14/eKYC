"""
Rate Limiter Service — M41 Redis upgrade
Redis backend with automatic in-memory fallback for dev/CI.
BFIU Circular No. 29 compliant limits.
All public function signatures unchanged from M28.
"""
import time
import threading
import logging
from typing import Optional
from app.services.redis_client import get_redis

log = logging.getLogger(__name__)

# ── BFIU-compliant rate limits ────────────────────────────────────────────
RATE_LIMITS = {
    "auth_token":  {"requests": 10,  "window_seconds": 60},
    "face_verify": {"requests": 30,  "window_seconds": 60},
    "nid_scan":    {"requests": 60,  "window_seconds": 60},
    "nid_verify":  {"requests": 60,  "window_seconds": 60},
    "liveness":    {"requests": 120, "window_seconds": 60},
    "bfiu_report": {"requests": 10,  "window_seconds": 60},
    "file_upload": {"requests": 30,  "window_seconds": 60},
    "default":     {"requests": 120, "window_seconds": 60},
}

# ── In-memory fallback store (thread-safe) ────────────────────────────────
_counters: dict = {}
_lock = threading.Lock()


def _get_key(endpoint: str, client_key: str) -> str:
    return f"rl:{endpoint}:{client_key}"


# ── Redis backend ─────────────────────────────────────────────────────────
def _check_redis(key: str, max_req: int, window_sec: int) -> tuple[int, float]:
    """
    Atomic Redis rate limit check using INCR + EXPIRE.
    Returns (count, reset_at).
    """
    r = get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    count, ttl = pipe.execute()

    if ttl == -1:   # key exists but has no expiry (race condition guard)
        r.expire(key, window_sec)
        ttl = window_sec
    elif ttl == -2 or count == 1:  # new key
        r.expire(key, window_sec)
        ttl = window_sec

    reset_at = time.time() + ttl
    return count, reset_at


# ── In-memory backend ─────────────────────────────────────────────────────
def _check_memory(key: str, max_req: int, window_sec: int) -> tuple[int, float]:
    now = time.time()
    with _lock:
        entry = _counters.get(key)
        if entry is None or now - entry["window_start"] >= window_sec:
            _counters[key] = {"count": 1, "window_start": now}
            count = 1
        else:
            _counters[key]["count"] += 1
            count = _counters[key]["count"]
        reset_at = _counters[key]["window_start"] + window_sec
    return count, reset_at


# ── Public API (signatures unchanged) ────────────────────────────────────
def check_rate_limit(endpoint: str, client_key: str) -> dict:
    """
    Check and increment rate limit counter.
    Returns: allowed, remaining, reset_at, limit.
    Uses Redis if available, in-memory otherwise.
    """
    cfg        = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    max_req    = cfg["requests"]
    window_sec = cfg["window_seconds"]
    key        = _get_key(endpoint, client_key)

    try:
        r = get_redis()
        if r is not None:
            count, reset_at = _check_redis(key, max_req, window_sec)
        else:
            count, reset_at = _check_memory(key, max_req, window_sec)
    except Exception as exc:
        log.warning("[M41] rate_limiter Redis error, falling back: %s", exc)
        count, reset_at = _check_memory(key, max_req, window_sec)

    remaining = max(0, max_req - count)
    allowed   = count <= max_req

    return {
        "allowed":        allowed,
        "remaining":      remaining,
        "limit":          max_req,
        "count":          count,
        "reset_at":       reset_at,
        "window_seconds": window_sec,
        "endpoint":       endpoint,
        "client_key":     client_key,
    }


def get_limit_config(endpoint: str) -> dict:
    return RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])


def get_all_limits() -> dict:
    return RATE_LIMITS


def reset_counters(endpoint: str = None, client_key: str = None):
    """Reset counters — for testing only."""
    r = get_redis()

    # Redis reset
    if r is not None:
        try:
            if endpoint and client_key:
                r.delete(_get_key(endpoint, client_key))
            elif endpoint:
                pattern = f"rl:{endpoint}:*"
                keys = r.keys(pattern)
                if keys:
                    r.delete(*keys)
            else:
                keys = r.keys("rl:*")
                if keys:
                    r.delete(*keys)
        except Exception as exc:
            log.warning("[M41] Redis reset error: %s", exc)

    # Always reset in-memory too
    with _lock:
        if endpoint and client_key:
            _counters.pop(_get_key(endpoint, client_key), None)
        elif endpoint:
            for k in [k for k in _counters if k.startswith(f"rl:{endpoint}:")]:
                _counters.pop(k, None)
        else:
            _counters.clear()


def get_stats() -> dict:
    """Return current counter stats and backend mode."""
    from app.services.redis_client import is_redis_available
    r = get_redis()
    if r is not None:
        try:
            keys = r.keys("rl:*")
            active_keys = len(keys)
            counters = {k: {"count": int(r.get(k) or 0)} for k in keys}
            return {
                "backend":     "redis",
                "active_keys": active_keys,
                "counters":    counters,
            }
        except Exception as exc:
            log.warning("[M41] get_stats Redis error: %s", exc)
    with _lock:
        mem_counters = {k: v.copy() for k, v in _counters.items()}
    return {
        "backend":     "memory",
        "active_keys": len(mem_counters),
        "counters":    mem_counters,
    }
