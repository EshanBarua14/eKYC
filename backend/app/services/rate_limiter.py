"""
Rate Limiter Service - M28
In-memory rate limiting for dev, Redis-ready for production.
BFIU Circular No. 29 compliant limits.
"""
import time
import threading
from typing import Optional

# ── BFIU-compliant rate limits ───────────────────────────────────────────
RATE_LIMITS = {
    "auth_token":       {"requests": 10,  "window_seconds": 60},
    "face_verify":      {"requests": 30,  "window_seconds": 60},
    "nid_scan":         {"requests": 60,  "window_seconds": 60},
    "nid_verify":       {"requests": 60,  "window_seconds": 60},
    "liveness":         {"requests": 120, "window_seconds": 60},
    "bfiu_report":      {"requests": 10,  "window_seconds": 60},
    "file_upload":      {"requests": 30,  "window_seconds": 60},
    "default":          {"requests": 120, "window_seconds": 60},
}

# ── In-memory store (thread-safe) ────────────────────────────────────────
_counters: dict = {}
_lock = threading.Lock()

def _get_key(endpoint: str, client_key: str) -> str:
    return f"{endpoint}:{client_key}"

def check_rate_limit(endpoint: str, client_key: str) -> dict:
    """
    Check and increment rate limit counter.
    Returns: allowed, remaining, reset_at, limit
    """
    cfg        = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    max_req    = cfg["requests"]
    window_sec = cfg["window_seconds"]
    key        = _get_key(endpoint, client_key)
    now        = time.time()

    with _lock:
        entry = _counters.get(key)
        if entry is None or now - entry["window_start"] >= window_sec:
            _counters[key] = {"count": 1, "window_start": now}
            count = 1
        else:
            _counters[key]["count"] += 1
            count = _counters[key]["count"]
        window_start = _counters[key]["window_start"]

    reset_at  = window_start + window_sec
    remaining = max(0, max_req - count)
    allowed   = count <= max_req

    return {
        "allowed":   allowed,
        "remaining": remaining,
        "limit":     max_req,
        "count":     count,
        "reset_at":  reset_at,
        "window_seconds": window_sec,
        "endpoint":  endpoint,
        "client_key": client_key,
    }

def get_limit_config(endpoint: str) -> dict:
    """Get rate limit config for an endpoint."""
    return RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])

def get_all_limits() -> dict:
    """Return all configured rate limits."""
    return RATE_LIMITS

def reset_counters(endpoint: str = None, client_key: str = None):
    """Reset counters — for testing only."""
    with _lock:
        if endpoint and client_key:
            key = _get_key(endpoint, client_key)
            _counters.pop(key, None)
        elif endpoint:
            keys = [k for k in _counters if k.startswith(f"{endpoint}:")]
            for k in keys:
                _counters.pop(k, None)
        else:
            _counters.clear()

def get_stats() -> dict:
    """Return current counter stats."""
    with _lock:
        return {
            "active_keys": len(_counters),
            "counters":    {k: v.copy() for k, v in _counters.items()},
        }
