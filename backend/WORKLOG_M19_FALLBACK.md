# Work Log — M19 Traditional KYC Fallback Handler
Date: 2026-04-18 21:57
Branch: main

## Summary
Built the Traditional KYC Fallback Handler (M19) — BFIU-mandated fallback
to physical document collection when eKYC fails technically.

## Files Created
- backend/app/services/fallback_service.py   (fallback state machine)
- backend/app/api/v1/routes/fallback.py      (9 endpoints)
- backend/tests/test_fallback.py            (23 tests, all passing)

## Files Modified
- backend/app/api/v1/router.py   (added fallback_router)

## Backend Endpoints (prefix: /api/v1/fallback)
  POST /create                 - Create fallback case with trigger code
  POST /{id}/document          - Upload physical document (NID, photo, signature)
  POST /{id}/review/start      - Agent picks up case for review
  POST /{id}/review/decide     - Approve or reject after document review
  GET  /{id}                   - Get case by case_id
  GET  /session/{session_id}   - Get case by original eKYC session
  GET  /queue/pending           - Cases awaiting review
  GET  /stats                   - Case statistics by status
  GET  /document-types          - Required documents per KYC type

## Trigger Codes
  NID_API_UNAVAILABLE    - EC NID server unavailable
  MAX_ATTEMPTS_EXCEEDED  - 10 NID attempts exhausted
  FACE_MATCH_FAILED      - Biometric failure repeated
  FINGERPRINT_FAILED     - Fingerprint failure repeated
  MANUAL_TRIGGER         - Agent decision
  TECHNICAL_ERROR        - General technical failure

## Fallback Flow
  INITIATED -> DOCS_PENDING -> DOCS_SUBMITTED -> UNDER_REVIEW -> APPROVED/REJECTED
  Required docs auto-tracked. Status advances when all docs submitted.

## Required Documents
  Simplified: NID_FRONT, NID_BACK, PHOTO, SIGNATURE
  Regular:    + UTILITY_BILL, INCOME_PROOF

## Test Results
  23 passed, 0 failed, 2 warnings
  Classes: TestCreateFallback(7) TestDocumentUpload(5)
           TestReviewFlow(5) TestGetCase(3) TestStatsAndTypes(3)

## Running Test Count
  Previous: 564 (M1-M18)
  Added:     23
  New total: 587 tests
