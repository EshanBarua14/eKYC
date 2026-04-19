# M33 Institution Onboarding Flow — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Built M33 institution onboarding — full lifecycle from application to activation.
Tests: 26 new tests added, 865/865 passing (was 839).

## What was built

### app/services/institution_onboarding_service.py
- submit_application(): create onboarding application (in-memory pipeline)
- get_application(), list_applications(): query applications
- start_review(): admin marks application UNDER_REVIEW
- add_review_note(): append notes during review
- approve_application(): create Institution in DB + generate client credentials
- reject_application(): reject with reason
- activate_institution(), suspend_institution(): lifecycle management
- get_onboarding_stats(): pipeline counts + active institutions
- reset_applications(): test isolation

### app/api/v1/routes/institution_onboarding.py
- POST /institutions/onboard/apply         - Public application submission
- GET  /institutions/onboard/applications  - List (ADMIN/AUDITOR)
- GET  /institutions/onboard/{id}          - Get application (ADMIN/AUDITOR)
- POST /institutions/onboard/{id}/review   - Start review (ADMIN)
- POST /institutions/onboard/{id}/note     - Add note (ADMIN)
- POST /institutions/onboard/{id}/approve  - Approve + create Institution (ADMIN)
- POST /institutions/onboard/{id}/reject   - Reject with reason (ADMIN)
- POST /institutions/onboard/{id}/activate - Activate institution (ADMIN)
- POST /institutions/onboard/{id}/suspend  - Suspend institution (ADMIN)
- GET  /institutions/onboard/stats         - Pipeline stats (ADMIN/AUDITOR)

### tests/test_m33_institution_onboarding.py
- 26 tests: Application, ListGet, Review, Approval, Rejection, Stats
- Tests full pipeline: APPLIED -> UNDER_REVIEW -> APPROVED
- Tests credential generation, duplicate prevention, state machine enforcement
