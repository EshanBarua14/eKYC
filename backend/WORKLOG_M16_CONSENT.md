# Work Log — M16 Digital Consent Gate
Date: 2026-04-18 16:06
Branch: main

## Summary
Built the Digital Consent Gate (M16) — mandatory explicit consent capture
before EC NID database query, as required by BFIU Circular No. 29 Section 3.2.

## Files Created
- backend/app/api/v1/routes/consent.py       (5 endpoints)
- frontend/src/components/ConsentGate.jsx    (modal consent UI)
- backend/tests/test_consent.py             (14 tests, all passing)

## Files Modified
- backend/app/api/v1/router.py              (added consent_router)
- frontend/src/components/NIDScanner.jsx    (consent gate inserted before onNIDCaptured)

## Backend Endpoints (prefix: /api/v1/consent)
  POST /record           - Record explicit consent (timestamp, IP, session_id, nid_hash)
  GET  /{session_id}    - Retrieve consent record
  POST /verify           - Gate check — 403 if no consent (blocks EC query)
  POST /{session_id}/revoke - Revoke consent
  GET  /list/all         - List all records for audit

## Consent Record Contains (BFIU §3.2)
  - consent_id (UUID), session_id, nid_hash
  - institution_id, agent_id, channel (SELF_SERVICE|AGENCY|BRANCH)
  - consent_text (full legal statement)
  - ip_address, user_agent, timestamp (UTC)
  - status (GRANTED|REVOKED), bfiu_ref, retention_years=5

## Frontend ConsentGate Modal
  - Appears after NID scan passes quality check
  - Shows: what data will be accessed (6 items from EC)
  - Full consent statement (scrollable)
  - Checkbox: must be ticked before proceeding
  - Warning: consent recorded with IP + timestamp for 5 years
  - I Consent button calls POST /consent/record then fires onNIDCaptured
  - Decline button aborts — user stays on NID scan step

## Flow Change (Critical)
  BEFORE: NID scan → Confirm & Continue → Liveness
  AFTER:  NID scan → Confirm & Continue → ConsentGate modal → EC query → Liveness
  EC database is now BLOCKED until consent is recorded.

## Test Results
  14 passed, 0 failed, 2 warnings (pre-existing Pydantic v2)
  Classes: TestConsentRecord(5) TestConsentGet(2) TestConsentVerify(3)
           TestConsentRevoke(2) TestConsentList(2)

## Running Test Count
  Previous: 506 (M1-M15)
  Added:     14
  New total: 520 tests
