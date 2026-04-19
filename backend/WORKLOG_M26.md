# M26 DB Persistence Fix — Work Log
Date: 2026-04-19
Author: Eshan Barua

## Summary
Fixed all 698 tests after wiring in-memory stores to SQLAlchemy DB in M26.
Started at: 599 passed, 65 failed, 34 errors
Finished at: 698 passed, 0 failed, 0 errors

## Files Modified

### app/services/audit_service.py
- log_event() now validates event_type against AUDIT_EVENTS (raises ValueError on invalid)
- log_event() return dict now includes: retention_until, bfiu_ref, before_state, after_state, actor_role
- reset_audit_log() now actually deletes DB rows (was no-op)
- list_entries() now filters by actor_id
- get_dashboard_stats() now returns flat keys: face_verify_matched, screening_blocked, edd_triggered etc.
- query_log() now passes actor_id filter through

### app/services/outcome_service.py
- auto_route() fixed stale-read bug: re-reads DB after each transition (PENDING->SCREENING->RISK_GRADED)
- auto_route() now returns success idempotently for terminal states (APPROVED/REJECTED)
- checker_decide() fixed: checker_id now committed before transition opens new session
- transition() logic unchanged — correct

### app/services/bfiu_report_service.py
- section_1 now includes: total_approved, simplified_ekyc, regular_ekyc, auto_approved, pending_checker_review, rejected
- section_2 now includes: pep_flagged
- section_3 now includes: fallback_kyc_cases, fallback_approved, fallback_rejected, trigger_breakdown
- compliance_rate capped at 100.0 (was division bug returning >100)
- Uses calendar.month_name for period_month_name

### app/services/cmi_service.py
- cdbl_ref now generated as CDBL-{uuid} (was None)
- cdbl_code added to _row() return dict
- FAILED verdict now returns error dict (route raises 422)
- MARGIN_ACCOUNT and PORTFOLIO_MGT added to CMI_PRODUCTS
- _ALWAYS_REGULAR set handles BO_JOINT, BO_NRB, MARGIN_LOAN, MARGIN_ACCOUNT
- _row() normalizes legacy AUTO_APPROVED->ACTIVE and old bo_number prefixes
- duplicate returns already_exists:True key

### app/api/v1/routes/cmi.py
- Imports CMI_PRODUCTS (was missing)
- Returns bo_account key consistently from service result
- Raises 422 on FAILED verdict / service error
- Added /products endpoint

### app/api/v1/routes/fallback.py
- /document-types endpoint now returns trigger_codes key
- submit_document route returns structured response with missing_docs/submitted_docs
- start_review route returns {"success","case"} structure
- decide_case route validates decision before calling service (422 on invalid)

### app/services/fallback_service.py
- case_id format fixed: FKYC-{uuid} (was FKYC{uuid} missing dash)
- submit_document() validates doc_type against VALID_DOC_TYPES (returns error on invalid)
- submit_document() correctly removes from missing_docs and adds to submitted_docs
- start_review() blocks if missing_docs not empty (returns error)
- decide_case() validates APPROVE/REJECT decision
- Removed backward-compat aliases that were overwriting real functions
- MANUAL_TRIGGER added to TRIGGER_CODES

### app/api/v1/routes/notification.py
- channels transformed from dict to list of {"channel":"SMS/EMAIL","status":...} dicts
- type field added: KYC_SUCCESS / KYC_FAILURE
- channels_notified uses len(channels_list)

### app/api/v1/routes/audit.py
- GET /log was missing return statement (returned None)

## Root Causes
1. Stale reads in auto_route() after DB transitions
2. Session boundary bug in checker_decide() losing checker_id
3. Backward-compat aliases at bottom of fallback_service.py overwrote real functions
4. Missing fields in return dicts (retention_until, bfiu_ref, actor_role, before_state)
5. Missing return statement in audit GET /log route
6. cdbl_ref never set on BOAccount creation
