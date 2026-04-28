# G11 — SECRET_KEY Production Enforcement
**BFIU Circular No. 29 §4.5 — Encryption key management**
**Date:** 2026-04-28
**Tests:** 5 passed, 0 failed

## Problem
`production_secrets_check` model_validator logged `log.error()` but did NOT raise.
Server could start in production with default `dev-secret-change-in-production` key.
JWT tokens signed with known key = full auth bypass risk.

## Fix
`app/core/config.py` — replaced `log.error(msg)` with `log.critical(msg)` + `raise ValueError(msg)`.
Production startup (DEBUG=False) now hard-crashes if SECRET_KEY is default, empty, or under 32 chars.
Dev mode (DEBUG=True) still only warns.

## Tests
`tests/test_g11_secret_key_enforcement.py` — 5 cases:
- Default key crashes in prod
- Short key crashes in prod
- Empty key crashes in prod
- Strong 64-char hex key passes in prod
- Default key allowed in dev (warn only)

## BFIU Compliance
§4.5 — Encryption keys must be properly managed. Hard enforcement on startup.
