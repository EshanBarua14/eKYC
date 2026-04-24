# M60 Work Log — COMPLIANCE_OFFICER Role + EDD Approval Workflow
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §4.2, §4.3

## What was built
- app/db/models_edd.py — EDDCase + EDDAction ORM models, BST timestamps
- app/services/edd_service.py — full EDD business logic
- app/api/v1/edd_router.py — 10 REST endpoints
- app/worker/tasks_edd.py — Celery beat SLA enforcement tasks
- alembic/versions/m60_edd_workflow.py — DB migration

## BFIU compliance
- COMPLIANCE_OFFICER role — Chief AML/CFT Officer
- CHECKER blocked from EDD approval (HTTP 403)
- EDD state machine: OPEN->INFO_REQUESTED->UNDER_REVIEW->APPROVED/REJECTED
- 1-month SLA auto-close for existing customers (§4.3)
- Immediate closure for irregular activity (§4.3)
- edd_actions append-only immutability trigger (§5.1)
- All timestamps BST UTC+6

## Test results
- M60: 29/29 passed
- Full suite: 1353 passed, 0 failures, 7 skipped
