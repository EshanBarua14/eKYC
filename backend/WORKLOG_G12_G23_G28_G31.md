# G12, G23, G28, G31 — Verification Audit
**Date:** 2026-04-28

## G12 — Redis AOF Persistence
**Status:** DONE (docker-compose.yml)
- `--appendonly yes` + `--appendfsync everysec`
- `redis_data` volume mounted
- BFIU §4.5 — Celery beat tasks survive restart

## G23 — Structured JSON Logging
**Status:** DONE (app/core/logging_config.py — M65)
- JSONFormatter outputs single-line JSON
- BST timestamps on all records
- Request-ID injected per request
- Wired in app/main.py via configure_logging()

## G28 — PII Masking in Logs
**Status:** DONE (app/core/logging_config.py — M65)
- NID number/hash: redacted to ****REDACTED
- Mobile (BD 01x format): masked to 01x****xxx
- Email: masked to fi***@domain.com
- _mask_pii() applied to all JSON log output

## G31 — Exit List Fully Wired
**Status:** DONE (app/services/screening_service.py + exit_list_service.py)
- ExitListEntry + ExitListAuditLog models exist
- screen_exit_list() called in run_full_screening()
- exit_list_entries + exit_list_audit_log tables in PostgreSQL
- API routes: POST /screening/exit-list/add + /screening/exit-list/check

## BFIU Compliance
- §4.5: Redis AOF, structured logging, PII masking
- §5.1: Audit trail integrity
- §5.3: Exit list screening in full screening pipeline
