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
