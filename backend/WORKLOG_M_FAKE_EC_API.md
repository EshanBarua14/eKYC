# WORKLOG — Fake EC NID Verification API

**Date:** 2026-05-03
**Module:** fake_ec_api (replaces in-memory DEMO mode)
**BFIU Ref:** Circular No. 29 — Section 3.2 / 3.3

---

## Problem

`nid_api_client.py` DEMO mode used an in-memory Python dict for NID lookups.
No persistence, no Swagger visibility, no audit trail, not extendable.

## Solution

Standalone FastAPI service (`fake_ec_api/`) on **port 8001** backed by **PostgreSQL**.
Replaces in-memory DEMO — eKYC app's `nid_api_client.py` calls this via `FAKE_EC` mode.

---

## Files Created

| File | Purpose |
|------|---------|
| `fake_ec_api/main.py` | FastAPI app — all endpoints + Swagger docs |
| `fake_ec_api/database.py` | SQLAlchemy models + PostgreSQL seed data |
| `fake_ec_api/requirements.txt` | fastapi, uvicorn, sqlalchemy, psycopg2-binary |
| `fake_ec_api/test_fake_ec_api.py` | 31 pytest test cases |
| `backend/platform_settings.json` | Sets `nid_api_mode = FAKE_EC` |

## Files Modified

| File | Change |
|------|--------|
| `backend/app/services/nid_api_client.py` | Added `FAKE_EC` mode + `_fake_ec_lookup()` + `_fake_ec_get_token()` |

---

## Database

- **DB:** `fake_ec_db` on localhost:5432
- **User:** `ec_api_user` / `ec_api_pass_2026`
- **Tables:** `nid_records`, `ec_institutions`, `ec_audit_log`

### Seeded NIDs (9 records)

| NID | Name | Type | Status |
|-----|------|------|--------|
| `2375411929` | ESHAN BARUA | SMART | ACTIVE |
| `19858524905063671` | MD ABUL MOSHAD CHOWDHURY | OLD_SMART | ACTIVE |
| `1234567890123` | RAHMAN HOSSAIN CHOWDHURY | SMART | ACTIVE |
| `9876543210987` | FATEMA BEGUM | SMART | ACTIVE |
| `1111111111111` | KARIM UDDIN AHMED | LAMINATED | ACTIVE |
| `2222222222222` | NASRIN SULTANA | SMART | ACTIVE |
| `3333333333333` | MOHAMMAD RAFIQUL ISLAM | SMART | ACTIVE |
| `4444444444444` | SHIRIN AKTER | SMART | ACTIVE |
| `0000000000000` | BLOCKED TEST CITIZEN | SMART | BLOCKED |

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth` | No | Get Bearer token |
| POST | `/api/v1/verify` | Bearer | Verify NID → full citizen record |
| POST | `/api/v1/verify/dob` | Bearer | Verify NID + DOB |
| GET  | `/api/v1/verify/{nid}` | Bearer | GET-style lookup |
| GET  | `/api/v1/nids` | No | List all NID records |
| POST | `/api/v1/nids` | No | Seed new NID |
| DELETE | `/api/v1/nids/{nid}` | No | Delete NID |
| GET  | `/api/v1/audit` | No | Audit log (BFIU §4) |
| GET  | `/api/v1/status` | No | Status + record counts |
| GET  | `/health` | No | Liveness probe |
| GET  | `/docs` | No | **Swagger UI** |

---

## How to Run

```bash
# 1. Start PostgreSQL (if not running)
service postgresql start

# 2. Start Fake EC API
cd fake_ec_api
uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# 3. Open Swagger UI
# http://127.0.0.1:8001/docs

# 4. Start main eKYC app (uses FAKE_EC mode via platform_settings.json)
cd ../backend
uvicorn main:app --port 8000 --reload
```

---

## Test Results

```
31 passed in 0.99s
```

### Test coverage:
- System: health, status
- Auth: valid, second institution, wrong secret, unknown client, suspended, no token, invalid token
- Verify: all 8 NIDs found, not found, blocked, invalid format (short/letters), spaces cleaned, session_id returned
- Verify+DOB: correct DOB, wrong DOB, not found, invalid format, blocked
- GET endpoint: valid, not found
- Admin: list NIDs, seed NID, duplicate rejected, delete NID, audit log

---

## nid_api_client.py changes

Added `FAKE_EC` mode:
- `_get_nid_settings()` now returns `client_id` as 5th value
- `lookup_nid()` routes to `_fake_ec_lookup()` when mode=`FAKE_EC`
- `_fake_ec_get_token()` — authenticates against fake EC, caches token
- `_fake_ec_lookup()` — calls `POST /api/v1/verify`, maps response to existing contract
- Graceful fallback to DEMO if fake EC service is unreachable

---

## Compliance

- BFIU §3.3 NID verification via EC: ✅ (now real HTTP call, not in-memory)
- BFIU §4 audit trail: ✅ every lookup logged to `ec_audit_log` table
- Error codes match BFIU/EC spec: EC_NOT_FOUND, NID_BLOCKED, EC_AUTH_ERROR, DOB_MISMATCH
- NID format validation: 10/13/17 digit BD NID numbers
