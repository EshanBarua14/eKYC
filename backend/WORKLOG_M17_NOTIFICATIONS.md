# Work Log — M17 SMS/Email Notification Service
Date: 2026-04-18 21:48
Branch: main

## Summary
Built the SMS/Email Notification Service (M17) — mandatory account opening
notifications required by BFIU Circular No. 29. Sends success and failure
notifications via SMS + Email. Dev mode logs to console/memory, prod mode
uses SMTP + SMS gateway via env vars.

## Files Created
- backend/app/services/notification_service.py  (SMS + Email engine)
- backend/app/api/v1/routes/notification.py     (5 endpoints)
- backend/tests/test_notification.py            (19 tests, all passing)

## Files Modified
- backend/app/api/v1/router.py   (added notification_router)

## Dependency Added
- httpx==0.27.0 (required by TestClient in newer starlette)

## Backend Endpoints (prefix: /api/v1/notify)
  POST /kyc-success   - Success notification: name, account, branch, type, service no
  POST /kyc-failure   - Failure notification: reason + helpdesk number
  GET  /log           - Delivery log filtered by session_id (5yr retention)
  GET  /stats         - SMS/Email delivery statistics + provider config status
  GET  /templates     - View all notification templates

## BFIU Compliance (Circular No. 29)
  Success SMS contains: full name, account number, branch, account type, service number
  Failure SMS contains: reason code, helpdesk number, session reference
  Both channels: SMS (mandatory) + Email (if provided)
  Delivery log retained for audit (5 years per BFIU §5.1)

## Dev vs Prod Mode
  Dev  (default): logs to console + in-memory, no real SMS/SMTP calls
  Prod: set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMS_API_KEY env vars

## Test Results
  19 passed, 0 failed, 2 warnings (pre-existing Pydantic v2)
  Classes: TestSuccessNotification(6) TestFailureNotification(5)
           TestDeliveryLog(3) TestStats(3) TestTemplates(2)

## Running Test Count
  Previous: 520 (M1-M16)
  Added:     19
  New total: 539 tests
