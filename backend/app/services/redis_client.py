"""
Redis Client — M41 Production Setup
Singleton Redis connection with automatic in-memory fallback for dev/CI.
BFIU Circular No. 29 — session counters, rate limiting, idempotency keys.
"""
import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Try to import redis ───────────────────────────────────────────────────
try:
    import redis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

_client: Optional[object] = None
_redis_mode: bool = False   # True = Redis, False = in-memory fallback


def get_redis() -> Optional[object]:
    """
    Return a connected Redis client, or None if unavailable.
    Connection is attempted once at startup; failures fall back to in-memory.
    """
    global _client, _redis_mode

    if _client is not None:
        return _client if _redis_mode else None

    if not _REDIS_AVAILABLE:
        log.warning("[M41] redis-py not installed — using in-memory fallback")
        _redis_mode = False
        return None

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _client = client
        _redis_mode = True
        log.info("[M41] Redis connected: %s", redis_url)
        return _client
    except Exception as exc:
        log.warning("[M41] Redis unavailable (%s) — using in-memory fallback", exc)
        _client = object()   # sentinel so we don't retry every call
        _redis_mode = False
        return None


def is_redis_available() -> bool:
    """Return True if Redis is connected and usable."""
    return _redis_mode


def reset_redis_client() -> None:
    """Force reconnection attempt — for testing only."""
    global _client, _redis_mode
    _client = None
    _redis_mode = False
