# M64 — DB-Level Audit Immutability — BFIU Circular No. 29 §5.1
## Date: 2026-04
## BFIU: §5.1 immutable audit trail
### Done
- PostgreSQL trigger on audit_logs: blocks UPDATE/DELETE
- Application-level append-only enforced at DB level
- audit_logs table added to Alembic control
- Production hardening tests passing
