# M60 — EDD Workflow — BFIU Circular No. 29 §4.2/§4.3
## Date: 2026-04
## BFIU: §4.2 Enhanced Due Diligence, §4.3 EDD closure
### Done
- edd_cases and edd_actions tables (Alembic m60_edd_workflow.py)
- EDD state machine: OPEN→UNDER_REVIEW→CLOSED/ESCALATED
- COMPLIANCE_OFFICER role — sole authority to approve/reject EDD
- CHECKER explicitly blocked from EDD approval
- 1-month SLA auto-close via Celery beat
- Immediate closure on irregular activity
- 29 tests passing
