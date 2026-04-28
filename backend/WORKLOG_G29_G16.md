# G29 + G16 — CORS Lock + Admin IP Whitelist
**BFIU Circular No. 29 §4.5 — Access control and encryption key management**
**Date:** 2026-04-28
**Tests:** 9 passed, 0 failed

## G29 — CORS localhost stripped in production
**Problem:** ALLOWED_ORIGINS_LIST only warned on localhost origins in prod — never blocked.
**Fix:** app/core/config.py
- computed_field now strips localhost/127.0.0.1 origins in prod (DEBUG=False)
- model_validator raises ValueError at startup if ALL origins are localhost in prod
- Dev mode (DEBUG=True) unchanged

## G16 — Admin IP whitelist
**Problem:** ADMIN_IP_WHITELIST not set in .env — middleware allows all IPs (dev passthrough).
**Fix:** .env — added ADMIN_IP_WHITELIST= entry with production instructions
- app/middleware/admin_ip_whitelist.py already implemented (M66)
- Empty = allow all (dev), populated = restrict to listed IPs (prod)
- Protects: /api/v1/admin, /api/v1/pep/entries, /api/v1/users, /api/v1/institutions

## Tests — tests/test_g29_g16_cors_ip_whitelist.py (9 cases)
G29:
- localhost stripped in production
- only-localhost origins crash in production
- production origins pass
- localhost allowed in dev

G16:
- non-whitelisted IP blocked (403)
- whitelisted IP passes
- empty whitelist allows all (dev mode)
- non-admin path never blocked
- X-Forwarded-For header respected (proxy-aware)

## BFIU Compliance
§4.5 — CORS locked to production domain. Admin endpoints IP-restricted.
