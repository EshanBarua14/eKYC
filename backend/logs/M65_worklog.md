# M65 Work Log — Structured JSON Logging + PII Masking
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §5.1 — audit trail integrity + observability

## What was built
- app/core/logging_config.py — JSONFormatter, RequestContextFilter, configure_logging()
- app/middleware/logging_middleware.py — RequestLoggingMiddleware
- Pure stdlib — no external deps (python-json-logger/structlog not available offline)

## Features
- JSON lines output for Docker/ELK/Loki
- BST timestamps (UTC+6) on all records
- Request-ID injected into every log record
- User context (user_id, role, institution_id) extracted from JWT per request
- PII masking: NID REDACTED, mobile last 3 visible, email prefix masked
- Exception type + traceback in JSON on errors
- Log level configurable via LOG_LEVEL env var
- json_output=False for human-readable local dev

## Fixes
- Middleware order: RequestLoggingMiddleware added before register_error_handlers
  so error_boundary sets request.state.request_id first (Starlette reverse exec order)
- NID regex: full value now REDACTED not partially masked

## Test results
- M65 tests: 16/16 passed
- Full suite: 1444 passed, 0 failures, 7 skipped
