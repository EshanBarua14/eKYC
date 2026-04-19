# M42 — Celery Task Queue Work Log
**Date:** 2026-04-20
**Sprint:** Production Readiness — Phase A Infrastructure (P0)
**Status:** COMPLETE ✅

## Objective
Async NID verification queue, BFIU report generation jobs,
periodic review scheduler (Celery beat). Redis broker.

## Files Created
| File | Purpose |
|------|---------|
| `app/worker/__init__.py` | Worker package |
| `app/worker/celery_app.py` | Celery app, Redis broker/backend, beat schedule |
| `app/worker/tasks/__init__.py` | Tasks package |
| `app/worker/tasks/nid_verify.py` | Async NID verify, exponential backoff, 6hr max retry |
| `app/worker/tasks/bfiu_report.py` | Monthly BFIU report generation job |
| `app/worker/tasks/periodic_review.py` | Daily review scheduler by risk tier |
| `tests/test_m42_celery.py` | 26 tests — all passing |

## Celery Beat Schedule
| Task | Schedule | Purpose |
|------|----------|---------|
| `bfiu-monthly-report` | 1st of month 01:00 UTC | Auto BFIU compliance report |
| `periodic-review-scheduler` | Daily 02:00 UTC | KYC review queue by risk tier |
| `nid-retry-sweep` | Every 15 min | Re-queue stuck pending_verification sessions |

## NID Retry Policy
- Max retries: 12 (covers ~6 hours)
- Backoff: 60s → 120s → 240s … capped at 3600s
- EC unavailable → pending_verification state
- Max retries exceeded → permanent pending_verification with EC_TIMEOUT reason

## Periodic Review Frequencies (BFIU Section 5.7)
- HIGH risk: 365 days (notify 30 days before)
- MEDIUM risk: 730 days (notify 30 days before)
- LOW risk: 1825 days (notify 60 days before)

## To Start Workers (production)
```bash
# Worker
celery -A app.worker.celery_app worker --loglevel=info

# Beat scheduler
celery -A app.worker.celery_app beat --loglevel=info
```

## Test Results
| Stage | Result |
|-------|--------|
| M42 unit tests | 26 passed |
| Full suite | **891 passed, 0 failed** |
