# eKYC Backend Work Log

## M76 — Real PEP List Data Loading Script
**Date:** 2026-04-25 (BST)
**BFIU §:** 4.2
**Status:** ✅ Complete

### What was built
- `app/scripts/load_pep_data.py` — idempotent PEP loader, 3 sources:
  - `--source seed` — 22 Bangladesh seed PEPs (PM, President, Ministers, Military Chiefs, BB Governor, SOE heads, BSEC/IDRA)
  - `--source csv --file path.csv` — BFIU-format CSV ingestion with validation
  - `--source un_xml --file path.xml` — UN Consolidated Sanctions XML parser
- Upsert on `(full_name_en, category)` — safe to re-run
- Updates `pep_list_meta` table after each load
- All entries: `status=ACTIVE`, `edd_required=True`, `risk_level=HIGH`
- BST timestamps throughout

### Test results
- `tests/test_m76_pep_loader.py` — **34/34 passed**

### BFIU compliance
- §4.2: PEP/IP identification — seed covers all mandatory BD categories
- §4.2: EDD required flag set on all entries
- §4.2: pep_list_meta versioning for audit trail

## M77 — Account Opening Notification Dispatch
**Date:** 2026-04-25 (BST)
**BFIU §:** 3.2 Step 5
**Status:** ✅ Complete

### What was built
- `app/worker/tasks/notify_account_opening.py` — Celery tasks:
  - `notify.account_opening_success` — SMS + email on KYC approval
  - `notify.account_opening_failure` — SMS on rejection
  - max_retries=3, retry_delay=60s, acks_late=True
- Wired into `app/api/v1/routes/kyc_profile.py` — fires after db.commit()
- Non-blocking — notification failure never fails profile creation

## M78 — KYC Profile DB Persistence + Notification Wire
**Date:** 2026-04-25 (BST)
**BFIU §:** 6.1/6.2
**Status:** ✅ Complete

### What was built
- KYCProfile already persists to DB — confirmed route wired end-to-end
- `send_account_opening_success.delay()` called after every successful profile creation
- Notification failure wrapped in try/except — non-blocking

## M79 — Tenant Schema Auto-Provisioning
**Date:** 2026-04-25 (BST)
**BFIU §:** 5.2
**Status:** ✅ Complete

### What was built
- `app/services/tenant_provisioning.py`:
  - `provision_tenant_schema()` — CREATE SCHEMA IF NOT EXISTS, idempotent
  - `deprovision_tenant_schema()` — RENAME to archived_ (never DROP, §5.1 retention)
  - `add_schema_to_allowlist()` — runtime middleware allowlist update
  - SQL injection prevention via strict regex + reserved name blocklist
- Wired into `app/api/v1/routes/admin.py` institution creation

### Test results
- `tests/test_m77_m78_m79.py` — **33/33 passed**

### BFIU compliance
- §3.2 Step 5: customer notified on account opening via SMS + email
- §5.2: complete schema isolation per institution, auto-provisioned on onboard
- §5.1: deprovisioning archives (renames) schema — never drops (5-year retention)

## M80 — JWT RSA Key Rotation
**Date:** 2026-04-25 (BST)
**Status:** ✅ Complete
- `app/scripts/rotate_jwt_keys.py` — backup + generate + reload + audit log
- Cleanup keeps 5 most recent backups
- `--force` and `--dry-run` flags
- 13 tests passing

## M81 — Prometheus Alertmanager Wired
**Date:** 2026-04-25 (BST)
**Status:** ✅ Complete
- `monitoring/alertmanager/alertmanager.yml` — routes, receivers, inhibit rules
- Compliance receiver for UNSCR/EDD alerts
- Critical receiver for ops+CTO
- Wired into `docker-compose.monitoring.yml` and `monitoring/prometheus.yml`
- 12 tests passing

## M82 — Data Residency Enforcement
**Date:** 2026-04-25 (BST)
**BFIU §:** 5.2 + Circular 23
**Status:** ✅ Complete
- `app/middleware/data_residency.py` — blocks cross-border PII transfer
- Adds X-Data-Residency: BD-ONLY header to all PII endpoint responses
- ENV: DATA_RESIDENCY_ENFORCE=true/false
- Wired into app/main.py
- 13 tests passing

## M83 — Locust Load Test Suite
**Date:** 2026-04-25 (BST)
**Status:** ✅ Complete
- `load_tests/locustfile.py` — 500 concurrent onboardings
- EKYCOnboardingUser (agent) + EKYCCheckerUser tasks
- SLA targets: p99 face_verify<3s, profile<2s, screening<1s
- Results printed on test_stop event

## M84 — Integration Tests (real Redis + PostgreSQL)
**Date:** 2026-04-25 (BST)
**Status:** ✅ Complete
- `tests/test_m84_integration.py` — 20 tests, auto-skipped without INTEGRATION_TESTS=1
- PostgreSQL: pgcrypto, pep_entries seed, audit immutability, tenant provisioning E2E
- Redis: ping, session limits, rate limit TTL, AOF persistence check
- Celery: eager mode, beat schedule completeness
- Run: INTEGRATION_TESTS=1 DATABASE_URL=... REDIS_URL=... pytest tests/test_m84_integration.py

### Combined test results
- M80-M84: 105 passed, 20 skipped (integration), 0 failures

## M85 — Composite Identity Score
**Date:** 2026-04-26 (BST)
**BFIU §:** Annexure-2
**Status:** ✅ Complete

### What was built
- `app/services/composite_identity_score.py`
- Combines face confidence (50%) + NID match (30%) + DOB match (20%)
- Score 0–100, verdict: PASS / REVIEW / FAIL
- Hard floors: face < 0.30 → FAIL; face < 0.45 → REVIEW (BFIU §3.2)
- Hard floor: NID + DOB both unmatched → REVIEW
- `score_from_verification_result()` — convenience wrapper for existing service outputs
- Full audit trail: BST timestamp, weights, thresholds, inputs in result

### Test results
- `tests/test_m85_composite_identity_score.py` — **37/37 passed**

### BFIU compliance
- Annexure-2: face confidence thresholds enforced (min 45% for PASS)
- §3.2: NID + DOB cross-validation as secondary identity anchors
- Composite score surfaced in KYC profile for BFIU inspector audit
