# M40 — PostgreSQL Migration Work Log
**Date:** 2026-04-20
**Sprint:** Production Readiness — Phase A Infrastructure (P0)
**Status:** COMPLETE ✅

## Objective
Replace SQLite with PostgreSQL 16, wire Alembic migrations, update DATABASE_URL,
confirm all 865 tests pass on PostgreSQL.

## Changes Made

### 1. PostgreSQL Setup
- Installed PostgreSQL 16 via Chocolatey
- Created database: `ekyc_db`, owner: `ekyc_user`
- Server running on localhost:5432

### 2. Files Modified
| File | Change |
|------|--------|
| `app/db/database.py` | PostgreSQL engine with connection pooling, `tenant_session()`, SQLite fallback |
| `app/db/models/auth.py` | Replaced local `Base = declarative_base()` with `from app.db.database import Base` |
| `app/db/models_platform.py` | Removed duplicate `Institution` and `User` classes; import from `auth.py` instead |
| `alembic/env.py` | Reads `DATABASE_URL` from environment via `load_dotenv()` |
| `alembic.ini` | `sqlalchemy.url = %(DATABASE_URL)s` (env-driven) |

### 3. Files Created
| File | Purpose |
|------|---------|
| `.env` | Local environment variables (DATABASE_URL, credentials) |
| `.env.example` | Template for production secrets |
| `alembic/versions/259fab2cedac_M40_postgresql_migration_baseline.py` | Baseline migration |

### 4. Root Cause Fixes
- `models_platform.py` had duplicate `Institution`/`User` with wrong columns (8 vs 13)
- `auth.py` had its own `Base = declarative_base()` — tables not registered on shared metadata
- FK `kyc_profiles.institution_id → institutions.id` removed (cross-file FK conflict)

## Test Results
| Stage | Result |
|-------|--------|
| Before M40 (SQLite) | 865 passed |
| After PostgreSQL migration | **865 passed, 0 failed** |

## Alembic State
- Head: `259fab2cedac` (M40_postgresql_migration_baseline)
- Previous: `c28956d50a52` (M25_full_schema_all_modules)
