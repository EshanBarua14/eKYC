# M30 Error Boundary — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Built M30 error boundary — production-grade global exception handling.
No stack traces leak to clients. Every error has a request ID.
Tests: 22 new tests added, 794/794 passing (was 772).

## What was built

### app/middleware/error_boundary.py
- request_id_middleware: attaches X-Request-ID + X-Response-Time to every response
- http_exception_handler: structured JSON for all HTTP errors
- validation_exception_handler: field-level validation errors with details
- unhandled_exception_handler: catches all exceptions, logs server-side only
- register_error_handlers(): wires all handlers onto FastAPI app

### Error response format (BFIU Section 6.1 compliant)
{
  "error": {
    "code":       "NOT_FOUND",
    "message":    "...",
    "status":     404,
    "request_id": "uuid-v4",
    "timestamp":  "ISO-8601",
    "bfiu_ref":   "BFIU Circular No. 29 - Section 6.1",
    "details":    {...}  // optional field-level errors
  }
}

### app/main.py
- register_error_handlers(app) called AFTER include_router
  (critical — must be after router registration or FastAPI overwrites handlers)

### tests/test_m30_error_boundary.py
- 22 tests: RequestID, 404, 422, Auth errors, Error format, 500 handling
- Tests X-Request-ID header propagation
- Tests no stack trace leakage
- Tests custom request ID round-trip
- Tests unhandled exception returns safe 500 message

## Key decisions
- register_error_handlers MUST be called after all include_router calls
- Stack traces logged server-side only via Python logging
- Error messages never include internal details (DB passwords, file paths etc.)
