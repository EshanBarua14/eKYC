# M37 — UNSCR Live Feed Work Log
**Date:** 2026-04-20
**Sprint:** Production Readiness — Phase B BFIU Compliance (P0)
**Status:** COMPLETE ✅

## Objective
Daily automated pull from UN consolidated sanctions list.
PostgreSQL storage with FTS search_vector.
Alert on list update failures. Celery beat daily schedule.

## Files Created
| File | Purpose |
|------|---------|
| `app/services/unscr_service.py` | UN list pull, XML parse, PostgreSQL upsert, FTS search |
| `app/worker/tasks/unscr_pull.py` | Celery beat task — daily pull with 3x retry |
| `tests/test_m37_unscr.py` | 36 tests — model, pull, XML parse, search, Celery task |

## Files Modified
| File | Change |
|------|--------|
| `app/db/models_platform.py` | Added `UNSCREntry` and `UNSCRListMeta` ORM models |
| `app/db/models/__init__.py` | Exported `UNSCREntry`, `UNSCRListMeta` |
| `app/worker/celery_app.py` | Added `unscr-daily-pull` beat schedule (daily 00:30 UTC) |

## Database Schema
### `unscr_entries`
- `un_ref_id`, `entry_type` (INDIVIDUAL/ENTITY), `primary_name`
- `aliases` (JSON array), `search_vector` (FTS — name + aliases joined)
- `list_version` (YYYY-MM-DD), `is_active`, `committee`, `listed_on`

### `unscr_list_meta`
- Pull audit log: version, URL, total/new/removed entries, status, error

## Pull Pipeline
1. Fetch XML from `scsanctions.un.org` (SSL, 60s timeout)
2. Parse `INDIVIDUAL` and `ENTITY` elements via `root.iter()`
3. Upsert entries — mark old versions inactive
4. Record pull metadata in `unscr_list_meta`
5. On failure → record FAILED status + send compliance alert
6. Demo entries fallback when URL unreachable (dev/CI)

## Celery Beat Schedule
- Task: `pull_unscr_list_daily` — daily at 00:30 UTC
- Max retries: 3 (1hr apart = 3hr window)
- On max retries exceeded → permanent alert sent

## Search
- Token overlap scoring on `search_vector` (name + all aliases)
- Threshold: 0.85 fuzzy, 1.0 exact match
- Verdict: CLEAR | REVIEW | MATCH

## Test Results
| Stage | Result |
|-------|--------|
| M37 unit tests | 36 passed |
| Full suite | **1058 passed, 0 failed, 7 skipped** |
