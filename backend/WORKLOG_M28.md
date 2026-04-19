# M28 Rate Limiting — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Built M28 rate limiting — BFIU-compliant per-endpoint, per-client limits.
Tests: 27 new tests added, 748/748 passing (was 721).

## What was built

### app/services/rate_limiter.py
- Thread-safe in-memory rate counter (Redis-ready for production)
- BFIU-compliant limits: auth_token=10/min, face_verify=30/min, nid_scan=60/min
- check_rate_limit(): check + increment counter, returns allowed/remaining/reset_at
- reset_counters(): clear counters for testing
- get_stats(): active key counts

### app/middleware/rate_limit_dep.py
- FastAPI Depends() factory: rate_limit("endpoint")
- Returns 429 with RATE_LIMIT_EXCEEDED + Retry-After header

### app/api/v1/routes/rate_limits.py
- GET  /rate-limits         - View all BFIU limits
- POST /rate-limits/check   - Check + consume one request
- GET  /rate-limits/stats   - Active counter stats
- POST /rate-limits/reset   - Reset counters (admin/test)

### app/api/v1/router.py
- Registered rate_limits_router

### tests/test_m28_rate_limiting.py
- 27 tests: Config, Check, Enforcement, Reset, Stats, Service unit tests
- Tests 429 enforcement, client isolation, counter reset
