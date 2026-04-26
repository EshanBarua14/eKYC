# WORK LOG — M92: BFIU Gap Fixes G01 G02 G04 G07 G25 G32
**Date:** 2026-04-26
**Session:** Six code gap fixes for BFIU Circular No. 29 compliance
**Commit:** M92
**Tests:** 38 new tests, 656 total passing, 0 failed

---

## Gaps Fixed

### G01 — §4.2: Beneficial Ownership wired into Regular eKYC workflow
**Problem:** `BeneficialOwner` model existed (M38) but was never called as an
explicit workflow step. `make_decision` only checked session data passively.

**Fix — `kyc_workflow_engine.py`:**
- Added `"beneficial_owner"` to `REGULAR_STEPS` between `screening` and `risk_assessment`
- Added `submit_beneficial_owner()` function enforcing:
  - `has_beneficial_owner=True` requires `bo_name`, `bo_nid`, `bo_ownership_pct`, `bo_is_pep`, `bo_cdd_done`
  - `bo_cdd_done=False` → error `BO_CDD_INCOMPLETE` (hard block)
  - `bo_is_pep=True` → sets `bo_pep_flag=True` → EDD auto-triggered downstream

**Fix — `kyc_workflow.py`:**
- Added `BeneficialOwnerReq` Pydantic schema
- Added `POST /kyc-workflow/{id}/beneficial-owner` endpoint

---

### G02 — §6.1/§6.2: KYC Profile Form returned in decision response
**Problem:** `generate_kyc_profile_form()` was called inside `make_decision()`
but `kyc_form_ref` and `kyc_form_version` were not included in the returned dict.

**Fix — `kyc_workflow_engine.py`:**
- Added `kyc_form_ref` and `kyc_form_version` to `make_decision()` return dict
- Form reference now visible to API caller for BFIU audit trail

---

### G04 — §4.2: PEP/IP seed data auto-loaded on startup
**Problem:** `PEPEntry` DB table existed (M62) and `load_seed()` script existed,
but the table was always empty at startup — all real PEPs passed screening as CLEAR.

**Fix — `main.py`:**
- Added `_seed_pep_data()` startup hook called on every app start
- Checks if `PEPEntry` count == 0, calls `load_seed(db)` if so
- Graceful fallback: logs warning if DB not ready (SQLite/CI environments)
- Result: Bangladesh government PEP seed data loaded automatically

---

### G07 — §6.1: Nominee validation now blocks invalid data
**Problem:** `validate_nominee_from_data()` was called inside `submit_data_capture()`
but `NomineeValidationError` was caught by a broad `except Exception` and swallowed
as a warning. Invalid nominee data (e.g. digits in name, unknown relation) allowed through.

**Fix — `kyc_workflow_engine.py`:**
- Split exception handling: `NomineeValidationError` now caught separately
- Invalid nominee → `_error()` returned with `error_code="NOMINEE_INVALID"` (hard block)
- No nominee at all → still a warning (recommended, not mandatory per §6.1)
- Boundary: partially filled but invalid nominee = blocked; empty nominee = warning

---

### G25 — §4.5: AES-256 Encryption on nid_hash and signature_data
**Problem:** `app/db/models.py` (the single-file legacy model) defined:
- `signature_data = Column(Text, nullable=True)` — plain text
- `nid_hash = Column(String(64), nullable=True)` — plain text hash

**Fix — `app/db/models.py`:**
- Added import: `from app.db.encrypted_type import EncryptedString` with SQLite fallback
- Changed `signature_data` → `Column(EncryptedString, nullable=True)`
- Changed `nid_hash` → `Column(EncryptedString, nullable=True)`
- `models_platform.py` already used `EncryptedString` — now consistent across all models

---

### G32 — §3.3 Step 4: Wet/Electronic signature ENFORCED for high-risk
**Problem:** `make_decision()` only set `session["data"]["signature_compliance_warning"]`
and logged an audit event. High-risk accounts with DIGITAL/PIN signatures were
allowed to proceed — this violates BFIU §3.3 Step 4 explicitly.

**Fix — `kyc_workflow_engine.py`:**
- Replaced warning block with hard BLOCK returning:
  ```json
  {"error": true, "error_code": "SIGNATURE_REQUIRED", "decision": "BLOCKED"}
  ```
- `SIGNATURE_BLOCKED` audit event logged
- Only WET or ELECTRONIC signatures allowed for HIGH risk accounts
- DIGITAL/PIN remains allowed for LOW and MEDIUM risk
- Removed duplicate signature warning blocks that existed in the EDD branch

---

## Files Changed

```
backend/app/services/kyc_workflow_engine.py   REGULAR_STEPS, submit_beneficial_owner(),
                                               nominee blocking, signature hard-block,
                                               kyc_form_ref in response
backend/app/api/v1/routes/kyc_workflow.py     BeneficialOwnerReq, /beneficial-owner endpoint
backend/app/db/models.py                      EncryptedString for signature_data + nid_hash
backend/app/main.py                           _seed_pep_data() startup hook
backend/tests/test_m92_gap_fixes.py           38 new tests (NEW)
```

## Test Results

```
test_m92_gap_fixes.py:  38/38 passed
Full suite:             656 passed, 0 failed
                        (1057 skipped = PostgreSQL integration, expected in CI)
```

## Compliance Status After This Session

| Gap | Section | Before | After |
|-----|---------|--------|-------|
| G01 BO workflow | §4.2 | ❌ not wired | ✅ explicit step, enforced |
| G02 KYC form output | §6.1/§6.2 | ❌ not in response | ✅ returned in decision |
| G04 PEP seed data | §4.2 | ❌ empty table | ✅ auto-loaded on startup |
| G07 Nominee validation | §6.1 | ❌ warns only | ✅ blocks invalid data |
| G25 Field encryption | §4.5 | ❌ plain text | ✅ EncryptedString |
| G32 Signature enforcement | §3.3 Step 4 | ❌ warns only | ✅ hard BLOCK |

## Remaining Blockers

| # | Gap | Type |
|---|-----|------|
| G05 | EC/Porichoy API real credentials | External dependency (MOU required) |
| G06 | Real adverse media news API | External dependency |
| G09 | Docker Compose + Nginx + SSL | Infrastructure |
| G15 | OWASP pen-test | Security audit |
| G47 | EC/Porichoy MOU signed | Legal |
| G48 | BFIU legal review | Legal |
| G59 | Full Bangla UI | Frontend |
