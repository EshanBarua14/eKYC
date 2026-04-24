# M59 — UNSCR Live Feed + Bangladesh Standard Time
**Date:** 2026-04-24
**Sprint:** BFIU Circular No. 29 Compliance — P0 Screening
**Status:** COMPLETE ✅

## Objective
Wire UNSCR screening to PostgreSQL DB (populated daily from UN XML)
and set all platform timestamps to Bangladesh Standard Time (UTC+6).

## UNSCR Production Flow
1. Celery beat fires daily at 00:30 UTC
2. `pull_unscr_list_daily` task fetches UN consolidated XML
   from https://scsanctions.un.org/resources/xml/en/consolidated.xml
3. XML parsed → individuals + entities extracted with aliases
4. Upserted into `unscr_entries` table (list_version = YYYY-MM-DD)
5. Old versions marked inactive (audit trail preserved)
6. `screen_unscr()` queries DB via `unscr_service.search_unscr()`
7. Fallback to in-memory demo list if DB empty/unavailable

## Demo vs Production
| Mode | Source | Updated |
|------|--------|---------|
| DEMO | In-memory 7 entries | Never |
| PRODUCTION | PostgreSQL unscr_entries | Daily 00:30 UTC |

## Bangladesh Standard Time
- `app/core/timezone.py` — BST utility module
- `now_bst()`, `bst_isoformat()`, `bst_display()`
- All audit trail timestamps now BST (UTC+6)
- TZ=Asia/Dhaka set on process startup

## Files
| File | Purpose |
|------|---------|
| `app/core/timezone.py` | BST utility |
| `app/services/screening_service.py` | screen_unscr() → DB |
| `app/services/unscr_service.py` | DB search + XML pull |
| `app/worker/tasks/unscr_pull.py` | Celery daily task |

## Test Results
- Full suite: 1286 passed, 0 failed
