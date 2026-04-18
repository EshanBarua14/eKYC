# Work Log — M13 Admin Console
Date: 2026-04-18 15:17
Branch: main

## Summary
Built the Admin Console (M13) — a full 6-section management interface
for the Xpert eKYC platform, BFIU Circular No. 29 compliant.

## Files Created
- backend/app/api/v1/routes/admin.py   (256 lines, 6 route groups)
- frontend/src/components/AdminConsole.jsx  (676 lines, 6 tabs)
- backend/tests/test_admin.py          (44 tests, all passing)

## Files Modified
- backend/app/api/v1/router.py         (added admin_router import + include)
- frontend/src/App.jsx                 (added ADMIN portal + AdminConsole import + header button)

## Backend Endpoints Added (prefix: /api/v1/admin)
### 1. Institution Management
  GET    /institutions               list all institutions
  POST   /institutions               create institution (auto-generates schema_name)
  PUT    /institutions/{iid}         update institution
  DELETE /institutions/{iid}         delete institution

### 2. User Management
  GET    /users                      list users (filterable by role, institution_id)
  POST   /users                      create user (5 roles: admin/checker/maker/agent/auditor)
  PUT    /users/{uid}/activate       activate or deactivate user
  DELETE /users/{uid}               delete user

### 3. Threshold Editor
  GET    /thresholds                 get all 8 BFIU thresholds
  PUT    /thresholds                 update a single threshold by key
  POST   /thresholds/reset           reset all to BFIU defaults

### 4. Webhook Management
  GET    /webhooks                   list registered webhooks
  POST   /webhooks                   register new webhook with event subscriptions
  DELETE /webhooks/{wid}             delete webhook
  GET    /webhooks/logs              view recent delivery attempts

### 5. System Health
  GET    /health                     module status, rate limits, whitelisted domains

### 6. Audit Log Viewer
  GET    /audit-logs                 filter by event_type + severity
  GET    /audit-logs/export          export as JSON or CSV download

## Frontend Features
- 6-tab navigation: Institutions / Users / Thresholds / Webhooks / Health / Audit Logs
- Institution form: name, short_code, IP whitelist, auto schema generation
- User form: create with role selector, activate/deactivate toggle, delete
- Threshold editor: inline edit with change highlight, per-field Save, Reset Defaults
- Webhook form: URL + multi-select event subscription + secret field
- Delivery log viewer with status color coding
- Health dashboard: module grid (CheckItem), rate limits, whitelisted domains
- Audit log viewer: severity filter + event_type filter + JSON/CSV export
- Full design system: Card, Btn, Badge, Spinner, SectionTitle, StatGrid, CheckItem
- Theme toggle + Exit button in header

## Portal Switcher Update
PORTALS now = { CUSTOMER, AGENT, ADMIN }
"Admin Console" button added to header (yellow accent, distinct from Agent blue)

## Test Results
  44 passed, 0 failed, 1 warning (Pydantic v2 config deprecation — pre-existing)
  Coverage: all 6 route groups fully tested
  Test classes: TestInstitutions(7) TestUsers(9) TestThresholds(7) TestWebhooks(7) TestHealth(5) TestAuditLogs(6) + 3 parametrized

## Fixes Applied During Build
- URL prefix mismatch: tests used /v1/admin/ but app mounts at /api/v1/ — patched all test URLs
- FastAPI Query(regex=) deprecated → replaced with pattern= for Pydantic v2 compatibility

## Running Test Count
  Previous: 411 tests
  Added:     44 tests (including 3 parametrized role variants)
  New total: 455 tests
