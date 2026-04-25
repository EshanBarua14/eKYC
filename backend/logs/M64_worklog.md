# M64 Work Log — Production Readiness
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 — Infrastructure + §4.2, §5.1

## What was built

### M64-A: docker-compose.prod.yml
- Full stack: postgres, redis, backend, celery_worker, celery_beat, frontend, nginx, prometheus, grafana
- Two networks: ekyc_internal (isolated) + ekyc_external (nginx only)
- Persistent volumes for all stateful services
- JSON logging with rotation

### M64-B: backend/.env.production
- Complete production environment template
- All secrets documented with CHANGE_ME markers
- NID_API_MODE, SMS, SMTP, Redis password all parameterised

### M64-C: infra/postgres/postgresql.conf
- BST timezone (Asia/Dhaka), tuned memory settings

### M64-D: SECRET_KEY crash-if-default
- app/core/config.py: raises ValueError in production if SECRET_KEY is default/weak
- BFIU §4.5 — encryption keys must be properly managed

### M64-G: Audit log DB immutability trigger
- alembic/versions/m64_audit_immutability.py
- BEFORE UPDATE OR DELETE trigger on audit_logs (BFIU §5.1)
- audit_service.reset_audit_log() updated to use TRUNCATE (test-only)

### M64-H: Beneficial ownership wired into Regular KYC workflow
- kyc_workflow_engine.py: BO PEP flag check in submit_risk_assessment
- BO with is_pep=True triggers EDD (BFIU §4.2)
- bo_pep_flag propagated to make_decision

### M64-I: §6.1/§6.2 KYC profile form generator
- app/services/kyc_form_generator.py
- generate_kyc_profile_form() called at workflow completion
- §6.1 Simplified: NID, biometric, UNSCR, nominee, signature, notification
- §6.2 Regular: + PEP, adverse media, risk score, BO declared, source of funds
- NID masked to last 4 digits for PII protection

### M64-J: Wet signature enforcement
- HIGH risk accounts: WET or ELECTRONIC signature required (§3.3 Step 4)
- DIGITAL/PIN only acceptable for LOW/MEDIUM risk
- signature_compliant field in §6.2 form output

## Fixes during session
- generate_kyc_form import name fixed
- audit_service.reset_audit_log uses TRUNCATE not DELETE

## Test results
- M64 tests: 24/24 passed
- Full suite: 1428 passed, 0 failures, 7 skipped
