# M61 Work Log — Role-based Data Isolation
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §5.1, §5.2

## What was built
- app/services/data_isolation.py — isolation rules engine
- app/middleware/data_isolation_middleware.py — FastAPI Depends() callables
- tests/test_m61_data_isolation.py — 26 tests

## Rules enforced
- AUDITOR: globally read-only, write blocked HTTP 403 (§5.1)
- AGENT: own sessions/profiles only (agent_id filter)
- COMPLIANCE_OFFICER: KYC session writes blocked, EDD queue only (§4.3)
- CHECKER: review queue only, no KYC session creation
- All 403 errors carry BFIU §5.1 reference

## Resource maps defined per role
- ADMIN: full access
- AUDITOR: read all, write none
- AGENT: own records only
- COMPLIANCE_OFFICER: edd_cases write only
- CHECKER: review/approve verification_results only
- MAKER: kyc_sessions + kyc_profiles + nid_scans

## Test results
- M61 tests: 26/26 passed
- Full suite: 1379 passed, 0 failures, 7 skipped
