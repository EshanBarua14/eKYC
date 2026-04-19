# M32 2FA Enforcement — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Built M32 2FA enforcement — role-based TOTP requirement.
ADMIN and CHECKER roles must enroll TOTP before JWT is issued.
Tests: 23 new tests added, 839/839 passing (was 816).

## What was built

### app/services/twofa_service.py
- ROLES_REQUIRING_2FA: {ADMIN, CHECKER}
- ROLES_2FA_OPTIONAL: {MAKER, AUDITOR}
- ROLES_2FA_EXEMPT:   {AGENT}
- check_2fa_compliance(): validates role + totp_enabled + totp_code
- get_2fa_policy(): returns platform policy dict
- is_2fa_required(), is_2fa_exempt(): role checks

### app/api/v1/routes/auth.py (updated)
- Login now calls check_2fa_compliance() before issuing JWT
- ADMIN/CHECKER blocked with 2FA_SETUP_REQUIRED if TOTP not enrolled
- Returns action_required field for client to handle

### app/api/v1/routes/twofa.py (new)
- GET /auth/2fa/policy         - Platform 2FA policy (public)
- GET /auth/2fa/status         - Current user 2FA compliance
- GET /auth/2fa/required-roles - Roles requiring 2FA

### Tests updated for TOTP compliance
- test_m2_auth.py:     ADMIN/CHECKER login tests set up TOTP
- test_m8_risk.py:     CHECKER login fixed
- test_m9_screening.py: CHECKER login fixed
- test_m10_lifecycle.py: ADMIN login fixed
- test_m12_gateway.py:  ADMIN login fixed
- test_admin.py:        ADMIN login via TOTP
- test_m29_admin_auth.py: ADMIN/CHECKER via TOTP
- tests/test_helpers.py: shared TOTP login helper

### tests/test_m32_2fa.py (new)
- 23 tests: policy, role enforcement, TOTP flow, status, service unit tests
