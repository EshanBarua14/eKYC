# M67 Work Log — DB Backup + 5-Year Retention + pip freeze
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §5.1

## What was built
- scripts/backup_db.sh — daily pg_dump with BST timestamps, 30-day rotation
- app/worker/tasks_retention.py — monthly 5-year retention check task
- docker-compose.prod.yml — db_backup service added
- requirements.txt — pinned and frozen
- celery_app.py encoding fixed (Windows-1252 byte 0xa7)

## BFIU §5.1 compliance
- 5-year retention period enforced via RETENTION_YEARS=5
- Monthly Celery beat task flags eligible records for archival
- Backup script verifies file not empty, logs BST timestamp
- 30-day backup rotation (configurable via BACKUP_RETENTION_DAYS)

## Test results
- M67 tests: 15/16 passed, 1 skipped (Windows execute bit)
- Full suite: 1475 passed, 0 failures, 8 skipped
