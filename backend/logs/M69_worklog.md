# M69 Work Log — Exit List DB-backed
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §5.1

## What was built
- app/db/models_exit_list.py — ExitListEntry + ExitListAuditLog ORM models
- app/services/exit_list_service.py — DB-backed add/deactivate/screen
- alembic/versions/m69_exit_list_tables.py — DB migration
- screening_service.py — screen_exit_list() wired to DB, fallback to memory

## Features
- Per-institution exit list persisted in PostgreSQL
- NID exact match + fuzzy name match (threshold 0.80, M56 Bangla phonetic)
- ADMIN/CHECKER only can add/deactivate entries
- exit_list_audit_log append-only immutability trigger (§5.1)
- DB fallback to in-memory demo list when db=None
- Name normalised to uppercase before matching

## Test results
- M69 tests: 18/18 passed
- Full suite: 1514 passed, 0 failures, 8 skipped
