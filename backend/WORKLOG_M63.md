# M63 — Baseline Migration — Alembic Authority
## Date: 2026-04
### Done
- All tables registered under Alembic control
- Replaced create_all() with versioned migrations
- CREATE TABLE IF NOT EXISTS safe for fresh DB
- Alembic sole migration authority from this point
