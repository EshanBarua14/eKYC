# M61 — Role-Based Data Isolation — BFIU Circular No. 29 §5.1/§5.2
## Date: 2026-04
## BFIU: §5.1 audit trail, §5.2 data residency
### Done
- 6 roles enforced: ADMIN MAKER CHECKER AGENT AUDITOR COMPLIANCE_OFFICER
- AUDITOR read-only enforced across all endpoints
- AGENT own-records-only isolation
- Role-based data isolation middleware
- 26 tests passing
