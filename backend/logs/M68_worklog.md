# M68 Work Log — Nominee Validation
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §6.1/§6.2

## What was built
- app/services/nominee_validator.py — full nominee validation service
- kyc_workflow_engine.py — nominee validation wired into submit_data_capture

## Validation rules (BFIU §6.1)
- nominee_name: required, min 2 chars, letters only (English + Bangla)
- nominee_relation: required, must be from 20 allowed relations
- nominee_dob: optional, YYYY-MM-DD, nominee must be adult (>=18)
- Minor guardian flag for guardian nominees
- Name normalised to uppercase
- All errors reported together (not one-at-a-time)
- Missing nominee returns warning (not block) — strongly recommended

## Wired into workflow
- submit_data_capture() validates nominee on every data capture step
- NOMINEE_VALIDATED / NOMINEE_WARNING / NOMINEE_VALIDATION_FAILED in audit trail
- nominee_validated flag in session data

## Test results
- M68 tests: 21/21 passed
- Full suite: 1496 passed, 0 failures, 8 skipped
