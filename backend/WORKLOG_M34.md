# M34 — Election Commission NID API Client Work Log
**Date:** 2026-04-20
**Sprint:** Production Readiness — Phase B BFIU Compliance (P0)
**Status:** COMPLETE ✅

## Objective
HTTP client with retry/backoff, pending_verification state when EC is down,
Celery retry queue (max 6hrs, exponential backoff).

## Files Modified
| File | Change |
|------|--------|
| `app/services/nid_api_client.py` | Full M34 upgrade — retry logic, pending_verification, Celery enqueue |

## Files Created
| File | Purpose |
|------|---------|
| `tests/test_m34_nid_api_client.py` | 28 tests — DEMO/STUB/LIVE modes, retry, cross-match |

## Key Features

### EC Error Codes
| Code | Meaning |
|------|---------|
| `EC_UNAVAILABLE` | Connection failure / timeout → triggers retry queue |
| `EC_RATE_LIMITED` | HTTP 429 → triggers retry queue |
| `EC_AUTH_ERROR` | HTTP 401 → non-retryable |
| `EC_NOT_FOUND` | HTTP 404 → non-retryable |
| `EC_SERVER_ERROR` | HTTP 5xx → retryable |

### Retry Strategy
- Sync retries: 3 attempts with 1s/2s/3s delays within single request
- On exhaustion: returns `pending_verification` state immediately
- Async retry: enqueues `verify_nid_async` Celery task (60s initial delay)
- Celery task: exponential backoff 60s→3600s, max 12 retries (~6hrs)

### Modes
- `DEMO` — in-memory mock DB (3 realistic BD NID records)
- `STUB` — always returns synthetic record (offline dev)
- `LIVE` — real EC API with urllib3 retry adapter + timeout

## Test Results
| Stage | Result |
|-------|--------|
| M34 unit tests | 28 passed |
| Full suite | **947 passed, 0 failed** |
