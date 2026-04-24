# M63 Work Log — Alembic Full Migration Cleanup
Date: 2026-04-25 BST
BFIU Reference: Infrastructure — versioned schema required for audit compliance

## What was done
- alembic/versions/m63_baseline_missing_tables.py — baseline migration for 15 tables
  previously only managed by create_all()
- app/db/database.py — init_db() create_all() removed, Alembic is sole authority
- app/main.py — bare models.Base.metadata.create_all() removed
- tests/test_m36_fingerprint_sdk.py — fixed pre-existing TIMEOUT test (shared state bug)

## Tables now fully under Alembic control (24 total)
audit_logs, beneficial_owners, bfiu_reports, bo_accounts, bo_declarations,
consent_records, edd_actions, edd_cases, fallback_cases, institutions,
kyc_profiles, notification_logs, onboarding_outcomes, pep_audit_log,
pep_entries, pep_list_meta, unscr_entries, unscr_list_meta, uploaded_files,
user_sessions, users, webhook_deliveries, webhooks, agent_profiles

## Migration chain
c28956d50a52 -> 259fab2cedac -> 1e6df3c00319 -> b5a0d85cccf3
-> 20260424_205733 -> m60_edd_workflow -> m62_pep_tables -> m63_baseline_missing_tables

## Test results
- Full suite: 1404 passed, 0 failures, 7 skipped
- Pre-existing M36 timeout test fixed
