# M58 — KYC Workflow Engine
**Date:** 2026-04-24
**Sprint:** BFIU Circular No. 29 Compliance — P0 Core Flow
**Status:** COMPLETE ✅

## Objective
Full BFIU-compliant KYC workflow state machine with EC API
dual-mode (DEMO/LIVE) controlled from Admin UI platform_settings.json.

## Flows Implemented
**Simplified KYC (§2.3.1):**
data_capture → nid_verification → biometric → screening(UNSCR) → decision

**Regular KYC (§2.3.2):**
data_capture → nid_verification → biometric → screening(UNSCR+PEP) → risk_assessment → decision

## Decision Logic (§4.2, §6.3)
| Risk Grade | Decision |
|------------|----------|
| LOW | APPROVED (auto) |
| MEDIUM | CONDITIONAL (manual review) |
| HIGH / PEP | EDD_REQUIRED |
| UNSCR MATCH | REJECTED (hard block) |
| Bio fail | REJECTED (fallback after 3 sessions) |

## EC API Modes
- DEMO: in-memory NID database (3 demo NIDs)
- LIVE: real EC NID API with retry/backoff
- STUB: offline always-pass mode
- Controlled via platform_settings.json `nid_api_mode`

## Files
| File | Purpose |
|------|---------|
| `app/services/kyc_workflow_engine.py` | State machine engine |
| `app/api/v1/routes/kyc_workflow.py` | REST endpoints |
| `tests/test_m58_kyc_workflow.py` | 44 tests |

## Test Results
- M58 suite: 44 passed
- Full suite: 1286 passed, 0 failed
