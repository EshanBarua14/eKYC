# M29 Admin Auth — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Built M29 admin authentication — ALL admin endpoints now require JWT.
Production-grade RBAC with role enforcement.
Tests: 24 new tests (M29) + 44 test_admin.py upgraded to use JWT auth.
Total: 772/772 passing (was 748).

## What was built

### app/middleware/rbac.py
- require_admin(): ADMIN role only, returns 403 otherwise
- require_admin_or_auditor(): ADMIN or AUDITOR roles
- require_checker_or_above(): ADMIN or CHECKER roles
- require_role(*roles): generic factory for any role combination

### app/services/admin_service.py
- create_institution(): DB-backed institution creation
- list_institutions(), get_institution(), update_institution_status()
- create_admin_user(): DB-backed user creation with stub institution
- list_users(), get_user(), deactivate_user(), update_user_role()
- get_platform_stats(): institution + user counts

### app/api/v1/routes/admin.py (REWRITTEN)
- ALL endpoints now require JWT authentication
- Institution CRUD: create, list, get, update, delete, patch status
- User CRUD: create, list, get, activate/deactivate, delete, role update
- Threshold editor: get, update, reset (in-memory, BFIU compliant)
- Webhook management: create, list, delete, logs
- System health: requires ADMIN or AUDITOR (not public)
- Audit logs: list + export (json/csv)
- Stats: platform-wide counts (ADMIN only)

### tests/test_admin.py (UPGRADED)
- All 44 tests now use admin JWT headers
- Unique emails per run (no stale data conflicts)

### tests/test_m29_admin_auth.py (NEW)
- 24 tests: auth required, role enforcement, institution CRUD, user CRUD, auditor access

### tests/test_e2e_security.py
- Fixed health check test to use public gateway health endpoint

## Security decisions
- No unauthenticated admin endpoints — production requirement
- ADMIN role for write operations, AUDITOR for read-only
- JWT RS256 — same token system as all other endpoints
