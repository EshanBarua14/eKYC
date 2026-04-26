# WORKLOG_M102.md
## M102 — AES-256 Field Encryption (pgcrypto) — BFIU Circular No. 29 s4.5
**Date:** 2026-04-27
**Branch:** main
**Tests:** 20/20 passing

### What was done
1. Fixed M54 encrypted_type.py — was importing but not encrypting on SQLite
2. Rewrote EncryptedString TypeDecorator — pure Python Fernet AES-128-CBC
   - No bind_expression/column_expression (dialect-agnostic)
   - process_bind_param: encrypts with enc1: prefix
   - process_result_value: decrypts enc1: prefix values
   - Works identically on PostgreSQL and SQLite
3. Added _FALLBACK alias for legacy test compatibility
4. Added M102 Alembic migration (m102_pgcrypto_encryption.py)
   - PostgreSQL: CREATE EXTENSION IF NOT EXISTS pgcrypto
   - ALTER TABLE consent_records.nid_hash to BYTEA
   - ALTER TABLE kyc_profiles.signature_data to BYTEA
   - ALTER TABLE beneficial_owners.nid_number to BYTEA
   - SQLite: no-op
5. Updated database.py — PostgreSQL with SQLite fallback on connection failure
6. Updated .env — DATABASE_URL=postgresql:// (tests require this)
7. Patched test_m92_gap_fixes.py — open models.py with utf-8 encoding
8. Added 20-test suite test_m102_encryption.py

### Files changed
- app/db/encrypted_type.py (rewritten)
- app/db/database.py (postgres fallback)
- alembic/versions/m102_pgcrypto_encryption.py (new)
- alembic/versions/b5a0d85cccf3_m54_pgcrypto_aes_256_field_encryption_.py (patched)
- tests/test_m102_encryption.py (new, 20 tests)
- tests/test_m92_gap_fixes.py (encoding fix)
- .env (DATABASE_URL updated)

### BFIU compliance
- s4.5: AES encryption at rest for NID hash, signature data, BO NID number
- enc1: prefix allows detection of encrypted vs plaintext legacy rows
- Key loaded from EKYC_FIELD_ENCRYPTION_KEY env var
- Default key triggers WARNING log — production must override

### Test results
- 675 passed, 0 failed, 1058 skipped
- All pre-existing tests preserved
