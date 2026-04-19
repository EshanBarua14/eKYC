# M41 — Redis Production Setup Work Log
**Date:** 2026-04-20
**Sprint:** Production Readiness — Phase A Infrastructure (P0)
**Status:** COMPLETE ✅

## Objective
Wire Redis for session counters, rate limiting, and idempotency keys.
Automatic fallback to in-memory when Redis unavailable (dev/CI mode).

## Files Created
| File | Purpose |
|------|---------|
| `app/services/redis_client.py` | Singleton Redis connection, auto-fallback, ping-on-connect |
| `app/services/idempotency.py` | Idempotency key store, 24hr TTL, Redis + in-memory fallback |

## Files Modified
| File | Change |
|------|--------|
| `app/services/rate_limiter.py` | Redis INCR+EXPIRE backend, in-memory fallback, get_stats() reads Redis keys |
| `app/services/session_limiter.py` | Redis INCR+EXPIRE for session/attempt counters, midnight TTL for sessions |
| `tests/conftest.py` | Redis cleanup fixture: flushes rl:*, sess:*, att:*, idem:* before test suite |

## Architecture
- Redis available → atomic INCR + EXPIRE (race-condition safe)
- Redis unavailable → thread-safe in-memory dict (dev/CI)
- Fallback is transparent — all function signatures unchanged
- Session keys expire at next midnight UTC (BFIU daily limit resets correctly)
- Attempt keys expire after 24hr TTL
- Idempotency keys: 24hr TTL per BFIU anti-replay requirement

## Key Decisions
- `socket_connect_timeout=2` — fast fallback if Redis is down
- `decode_responses=True` — all Redis values are strings
- `reset_counters()` clears both Redis AND in-memory (test isolation)
- `get_stats()` reads from Redis when available for accurate counts

## Test Results
| Stage | Result |
|-------|--------|
| Before M41 | 865 passed |
| After Redis wiring | **865 passed, 0 failed** |

## Dependencies Added
- `redis==5.0.3`
