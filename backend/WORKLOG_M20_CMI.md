# Work Log — M20 CMI/BO Account Support
Date: 2026-04-18 22:01
Branch: main

## Summary
Built CMI/BO Account Support (M20) — Capital Market Intermediary
BO account opening via CDBL stub, 2026 BFIU thresholds enforced.

## Files Created
- backend/app/services/cmi_service.py    (CDBL stub + BO account engine)
- backend/app/api/v1/routes/cmi.py       (6 endpoints)
- backend/tests/test_cmi.py             (23 tests, all passing)

## Files Modified
- backend/app/api/v1/router.py   (added cmi_router)

## Backend Endpoints (prefix: /api/v1/cmi)
  POST /bo/open              - Open CDBL BO account after eKYC
  GET  /bo/{bo_number}       - Get BO account by number
  GET  /bo/session/{sid}     - Get BO account by session ID
  GET  /bo/list              - List all BO accounts
  GET  /thresholds           - 2026 BFIU CMI thresholds
  GET  /products             - BO product catalog

## 2026 BFIU Thresholds (Capital Markets)
  Simplified max deposit : BDT 15,00,000
  Regular min deposit    : BDT 15,00,001
  Margin account min     : BDT 5,00,000
  Portfolio mgmt min     : BDT 10,00,000

## BO Products (5 types)
  BO_INDIVIDUAL  - Standard individual (CDBL: BO-IND)
  BO_JOINT       - Joint account max 2 holders (CDBL: BO-JNT)
  BO_NRB         - Non-Resident Bangladeshi, always REGULAR
  MARGIN_ACCOUNT - Leveraged trading, always REGULAR
  PORTFOLIO_MGT  - Discretionary management, always REGULAR

## Auto-Approval Logic
  deposit <= 15,00,000 + LOW risk + MATCHED + no PEP -> ACTIVE instantly
  Anything else -> PENDING_REVIEW

## CDBL Integration
  Mode: STUB (returns realistic 1201XXXXXXXXXX BO numbers)
  Production: set CDBL_MODE=LIVE + API credentials

## Test Results
  23 passed, 0 failed, 2 warnings
  Classes: TestOpenBO(7) TestThresholdRouting(4) TestProducts(4)
           TestGetList(4) TestThresholdsAndCatalog(4)

## Running Test Count
  Previous: 587 (M1-M19)
  Added:     23
  New total: 610 tests
