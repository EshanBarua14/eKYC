"""
Idempotency Key Store — M41
Redis backend with in-memory fallback.
24-hour TTL per BFIU anti-replay requirements.
"""
import json
import time
import threading
import logging
from typing import Optional, Any
from app.services.redis_client import get_redis

log = logging.getLogger(__name__)

IDEMPOTENCY_TTL = 86400   # 24 hours

# ── In-memory fallback ────────────────────────────────────────────────────
_store: dict = {}
_lock = threading.Lock()


def _idem_key(key: str) -> str:
    return f"idem:{key}"


def get_cached_response(idempotency_key: str) -> Optional[dict]:
    """
    Return cached response for this idempotency key, or None if not found.
    """
    r = get_redis()
    if r is not None:
        try:
            val = r.get(_idem_key(idempotency_key))
            if val:
                return json.loads(val)
            return None
        except Exception as exc:
            log.warning("[M41] idempotency get Redis error: %s", exc)

    with _lock:
        entry = _store.get(idempotency_key)
        if entry is None:
            return None
        if time.time() - entry["stored_at"] > IDEMPOTENCY_TTL:
            del _store[idempotency_key]
            return None
        return entry["response"]


def store_response(idempotency_key: str, response: dict) -> None:
    """
    Store response under idempotency key with 24-hour TTL.
    """
    r = get_redis()
    if r is not None:
        try:
            r.setex(_idem_key(idempotency_key), IDEMPOTENCY_TTL, json.dumps(response))
            return
        except Exception as exc:
            log.warning("[M41] idempotency store Redis error: %s", exc)

    with _lock:
        _store[idempotency_key] = {
            "response":  response,
            "stored_at": time.time(),
        }


def delete_key(idempotency_key: str) -> None:
    """Delete an idempotency key (for testing)."""
    r = get_redis()
    if r is not None:
        try:
            r.delete(_idem_key(idempotency_key))
        except Exception:
            pass
    with _lock:
        _store.pop(idempotency_key, None)


def get_stats() -> dict:
    """Return idempotency store stats."""
    from app.services.redis_client import is_redis_available
    with _lock:
        mem_keys = len(_store)
    return {
        "backend":  "redis" if is_redis_available() else "memory",
        "mem_keys": mem_keys,
    }
