# Work Log — M15 Digital KYC PDF Generator
Date: 2026-04-18 15:58
Branch: main

## Summary
Built the Digital KYC PDF Certificate Generator (M15) — generates
BFIU-compliant signed PDF documents for every completed onboarding.
This is the legal compliance artifact required by BFIU Circular No. 29.

## Files Created
- backend/app/services/pdf_service.py     (ReportLab PDF generator)
- backend/app/api/v1/routes/kyc_pdf.py    (3 endpoints)
- backend/tests/test_kyc_pdf.py           (15 tests, all passing)

## Files Modified
- backend/app/api/v1/router.py            (added kyc_pdf_router)
- frontend/src/components/MatchReport.jsx (added Download KYC Certificate button)

## Dependency Added
- reportlab==4.2.5 (PDF generation)

## Backend Endpoints (prefix: /api/v1/kyc)
  POST /pdf/generate              - Generate PDF from verification data, cache by session_id
  GET  /profile/{session_id}/pdf  - Download PDF as application/pdf attachment
  GET  /pdf/list                  - List all generated PDFs (admin)

## PDF Document Contents (BFIU Circular No. 29 compliant)
  1. Header — Xpert eKYC branding, document reference, timestamp
  2. Verdict banner — MATCHED/REVIEW/FAILED with confidence score %
  3. Personal Information — EC-verified name, DOB, address, family names, PEP flag
  4. KYC Classification — KYC type, risk grade, risk score, EDD flag, screening result
  5. Biometric Scores — SSIM 35%, Histogram 30%, ORB 25%, Pixel 10% with weights
  6. Liveness Detection — pass/fail, score/max, BFIU Annexure-2 reference
  7. Session & Audit — session ID, timestamp, agent ID, geolocation, processing time
  8. Footer — retention policy (5 years), institution name, BFIU reference

## Frontend Change
  - MatchReport.jsx: Green "Download KYC Certificate (PDF)" button appears
    after MATCHED or REVIEW verdict
  - Calls POST /pdf/generate then GET /profile/{session_id}/pdf
  - Auto-downloads file as kyc_certificate_{session_id}.pdf
  - Shows success/error message inline

## Test Results
  15 passed, 0 failed, 2 warnings (pre-existing Pydantic v2)
  Classes: TestPDFService(4) TestGenerateEndpoint(5) TestDownloadEndpoint(4) TestListEndpoint(2)

## Running Test Count
  Previous: 491 (M1-M14)
  Added:     15
  New total: 506 tests
