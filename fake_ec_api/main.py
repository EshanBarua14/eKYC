"""
Fake Bangladesh Election Commission (EC) NID Verification API
=============================================================
Port  : 8001
DB    : PostgreSQL (fake_ec_db)
Docs  : http://localhost:8001/docs   ← Swagger UI
Redoc : http://localhost:8001/redoc

Replaces the in-memory DEMO mode in nid_api_client.py.
The main eKYC app calls this service when nid_api_mode = "FAKE_EC".

BFIU Circular No. 29 compliant error codes and response shapes.

Endpoints
---------
POST /api/v1/auth            — get Bearer token (institution login)
POST /api/v1/verify          — verify NID (main endpoint)
POST /api/v1/verify/dob      — verify NID + DOB match
GET  /api/v1/verify/{nid}    — GET-style lookup
GET  /api/v1/nids            — list all seeded NIDs (test helper)
POST /api/v1/nids            — add new NID record (test helper)
DELETE /api/v1/nids/{nid}    — remove NID record (test helper)
GET  /api/v1/audit           — view audit log
GET  /health                 — liveness probe
GET  /api/v1/status          — API status + stats
"""

import re
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Annotated

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import (
    create_tables, seed, get_db,
    NIDRecord, Institution, AuditLog,
)

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FAKE-EC] %(levelname)s  %(message)s",
)
log = logging.getLogger("fake_ec")

# ── In-memory token store (stateless enough for test service) ─────────────
_tokens: dict[str, dict] = {}
TOKEN_TTL = 3600

# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app_: FastAPI):
    create_tables()
    db = next(get_db())
    seed(db)
    count = db.query(NIDRecord).count()
    log.info("DB ready — %d NID records loaded", count)
    yield

# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Bangladesh Election Commission — NID Verification API (FAKE / TEST)",
    lifespan=lifespan,
    description="""
## ⚠️ This is a FAKE EC API for development and testing only.

Simulates the **Bangladesh Election Commission** NID verification service used
in the eKYC onboarding flow as required by **BFIU Circular No. 29**.

---

### Quick start

1. **Get a token** → `POST /api/v1/auth`
   ```json
   { "client_id": "inst_xpert_001", "client_secret": "sk_test_xpert_ekyc_secret_2026" }
   ```

2. **Verify an NID** → `POST /api/v1/verify`
   ```json
   { "nid_number": "2375411929" }
   ```

3. **Verify NID + DOB** → `POST /api/v1/verify/dob`
   ```json
   { "nid_number": "2375411929", "date_of_birth": "1994-08-14" }
   ```

---

### Seeded test NIDs

| NID | Name | Status |
|-----|------|--------|
| `2375411929` | ESHAN BARUA | ACTIVE |
| `19858524905063671` | MD ABUL MOSHAD CHOWDHURY | ACTIVE |
| `1234567890123` | RAHMAN HOSSAIN CHOWDHURY | ACTIVE |
| `9876543210987` | FATEMA BEGUM | ACTIVE |
| `1111111111111` | KARIM UDDIN AHMED | ACTIVE |
| `2222222222222` | NASRIN SULTANA | ACTIVE |
| `3333333333333` | MOHAMMAD RAFIQUL ISLAM | ACTIVE |
| `4444444444444` | SHIRIN AKTER | ACTIVE |
| `0000000000000` | BLOCKED TEST CITIZEN | BLOCKED → 403 |
| Any other | — | 404 NOT FOUND |

---

### Error codes

| Code | HTTP | Meaning |
|------|------|---------|
| `EC_AUTH_ERROR` | 401 | Bad token or credentials |
| `INSTITUTION_SUSPENDED` | 403 | Institution account suspended |
| `NID_BLOCKED` | 403 | NID blocked by EC |
| `EC_NOT_FOUND` | 404 | NID not in EC database |
| `INVALID_NID_FORMAT` | 422 | Not 10 / 13 / 17 digits |
| `DOB_MISMATCH` | 422 | DOB does not match record |
| `EC_RATE_LIMITED` | 429 | Rate limit exceeded |

---

*BFIU Circular No. 29 — Section 3.2 / 3.3*
""",
    version="1.0.0-fake",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Auth",    "description": "Institution authentication"},
        {"name": "Verify",  "description": "NID verification endpoints"},
        {"name": "Admin",   "description": "Test helpers — seed / inspect NID records"},
        {"name": "System",  "description": "Health and status"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ── Helpers ───────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _valid_nid(nid: str) -> bool:
    return bool(re.fullmatch(r"\d{10}|\d{13}|\d{17}", nid.strip()))

def _issue_token(client_id: str, scope: str) -> str:
    token = f"ec_{uuid.uuid4().hex}"
    _tokens[token] = {
        "institution_id": client_id,
        "scope": scope,
        "exp": time.time() + TOKEN_TTL,
    }
    return token

def _log_audit(db: Session, institution_id: str, nid: str,
               endpoint: str, result: str, reason: str = None):
    db.add(AuditLog(
        request_id     = str(uuid.uuid4())[:8],
        institution_id = institution_id,
        nid_last4      = nid[-4:] if len(nid) >= 4 else nid,
        endpoint       = endpoint,
        result         = result,
        reason         = reason,
    ))
    db.commit()

# ── Auth dependency ───────────────────────────────────────────────────────

def require_token(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    info = _tokens.get(creds.credentials)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "EC_AUTH_ERROR",
                    "message": "Invalid or missing token. Call POST /api/v1/auth first."},
        )
    if time.time() > info["exp"]:
        del _tokens[creds.credentials]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "EC_AUTH_ERROR",
                    "message": "Token expired. Re-authenticate."},
        )
    return info

# ── Pydantic schemas ──────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    client_id:     str = Field(..., example="inst_xpert_001")
    client_secret: str = Field(..., example="sk_test_xpert_ekyc_secret_2026")

    model_config = {"json_schema_extra": {
        "example": {
            "client_id":     "inst_xpert_001",
            "client_secret": "sk_test_xpert_ekyc_secret_2026",
        }
    }}

class AuthResponse(BaseModel):
    access_token:     str
    token_type:       str = "Bearer"
    expires_in:       int = TOKEN_TTL
    scope:            str
    institution_name: str
    issued_at:        str

class NIDVerifyRequest(BaseModel):
    nid_number: str = Field(..., example="2375411929",
                            description="10, 13, or 17 digit BD NID number")
    session_id: Optional[str] = Field(None, example="sess_20260503_abc123")

    @field_validator("nid_number")
    @classmethod
    def clean(cls, v):
        return v.strip().replace(" ", "").replace("-", "")

    model_config = {"json_schema_extra": {
        "example": {"nid_number": "2375411929", "session_id": "sess_20260503_abc123"}
    }}

class NIDVerifyWithDOBRequest(BaseModel):
    nid_number:    str = Field(..., example="2375411929")
    date_of_birth: str = Field(..., example="1994-08-14",
                               description="YYYY-MM-DD")
    session_id:    Optional[str] = Field(None, example="sess_20260503_abc123")

    @field_validator("nid_number")
    @classmethod
    def clean(cls, v):
        return v.strip().replace(" ", "").replace("-", "")

    @field_validator("date_of_birth")
    @classmethod
    def valid_dob(cls, v):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
            raise ValueError("date_of_birth must be YYYY-MM-DD")
        return v.strip()

    model_config = {"json_schema_extra": {
        "example": {"nid_number": "2375411929",
                    "date_of_birth": "1994-08-14",
                    "session_id": "sess_20260503_abc123"}
    }}

class NIDRecordOut(BaseModel):
    nid_number:        str
    smart_card_number: Optional[str]
    pin:               Optional[str]
    full_name_en:      str
    full_name_bn:      str
    date_of_birth:     str
    fathers_name_en:   Optional[str]
    fathers_name_bn:   Optional[str]
    mothers_name_en:   Optional[str]
    mothers_name_bn:   Optional[str]
    spouse_name_en:    Optional[str]
    spouse_name_bn:    Optional[str]
    present_address:   Optional[str]
    permanent_address: Optional[str]
    place_of_birth:    Optional[str]
    district:          Optional[str]
    division:          Optional[str]
    blood_group:       Optional[str]
    gender:            str
    nationality:       Optional[str]
    religion:          Optional[str]
    occupation:        Optional[str]
    education:         Optional[str]
    issue_date:        Optional[str]
    expiry_date:       Optional[str]
    photo_url:         Optional[str]
    nid_type:          Optional[str]
    status:            str

    class Config:
        from_attributes = True

class NIDVerifyResponse(BaseModel):
    success:     bool
    nid_number:  str
    session_id:  Optional[str]
    source:      str
    verified_at: str
    bfiu_ref:    str
    data:        NIDRecordOut

class NIDSeedRequest(BaseModel):
    nid_number:    str
    full_name_en:  str
    full_name_bn:  str
    date_of_birth: str
    gender:        str
    fathers_name_en: Optional[str] = None
    mothers_name_en: Optional[str] = None
    present_address: Optional[str] = None
    blood_group:     Optional[str] = None
    religion:        Optional[str] = None
    occupation:      Optional[str] = None
    district:        Optional[str] = None
    division:        Optional[str] = None
    status:          str = "ACTIVE"
    nid_type:        str = "SMART"


# ── Routes ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"],
         summary="Liveness probe")
def health():
    return {"status": "ok", "service": "Fake EC NID API", "timestamp": _now()}


@app.get("/api/v1/status", tags=["System"],
         summary="API status and record count")
def api_status(db: Session = Depends(get_db)):
    total    = db.query(NIDRecord).count()
    active   = db.query(NIDRecord).filter_by(status="ACTIVE").count()
    blocked  = db.query(NIDRecord).filter_by(status="BLOCKED").count()
    audit_ct = db.query(AuditLog).count()
    return {
        "status":         "OPERATIONAL",
        "version":        "1.0.0-fake",
        "environment":    "TEST",
        "nid_records":    {"total": total, "active": active, "blocked": blocked},
        "audit_entries":  audit_ct,
        "active_tokens":  len(_tokens),
        "note":           "FAKE EC API — for development use only",
        "timestamp":      _now(),
    }


# ── Auth ──────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/auth",
    tags=["Auth"],
    response_model=AuthResponse,
    summary="Get Bearer token",
    responses={
        200: {"description": "Token issued"},
        401: {"description": "Invalid credentials",
              "content": {"application/json": {"example":
                  {"detail": {"error_code": "EC_AUTH_ERROR",
                              "message": "Invalid client_id or client_secret"}}}}},
        403: {"description": "Institution suspended",
              "content": {"application/json": {"example":
                  {"detail": {"error_code": "INSTITUTION_SUSPENDED",
                              "message": "Institution account has been suspended"}}}}},
    },
)
def authenticate(req: AuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate an institution and receive a Bearer token.

    Use the token in `Authorization: Bearer <token>` header for all verify endpoints.

    **Test credentials:**
    - `inst_xpert_001` / `sk_test_xpert_ekyc_secret_2026`
    - `inst_test_bank` / `sk_test_bank_secret_2026`
    """
    inst = db.query(Institution).filter_by(client_id=req.client_id).first()
    if not inst or inst.client_secret != req.client_secret:
        raise HTTPException(status_code=401, detail={
            "error_code": "EC_AUTH_ERROR",
            "message":    "Invalid client_id or client_secret",
        })
    if inst.status == "suspended":
        raise HTTPException(status_code=403, detail={
            "error_code": "INSTITUTION_SUSPENDED",
            "message":    "Institution account has been suspended",
        })
    token = _issue_token(inst.client_id, inst.scope)
    log.info("[AUTH] Token issued: institution=%s", inst.name)
    return AuthResponse(
        access_token=token,
        scope=inst.scope,
        institution_name=inst.name,
        issued_at=_now(),
    )


# ── Verify ────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/verify",
    tags=["Verify"],
    response_model=NIDVerifyResponse,
    summary="Verify NID number",
    responses={
        200: {"description": "NID found and verified"},
        401: {"description": "Invalid token"},
        403: {"description": "NID is blocked"},
        404: {"description": "NID not found"},
        422: {"description": "Invalid NID format"},
    },
)
def verify_nid(
    req:        NIDVerifyRequest,
    token_info: dict = Depends(require_token),
    db:         Session = Depends(get_db),
):
    """
    Main NID verification endpoint.

    Looks up the NID in the EC PostgreSQL database and returns the full
    citizen record. Logs every request to the audit table.

    **BFIU Circular No. 29 §3.3** — NID verification via Election Commission.
    """
    nid = req.nid_number

    if not _valid_nid(nid):
        raise HTTPException(status_code=422, detail={
            "error_code": "INVALID_NID_FORMAT",
            "message":    f"NID must be 10, 13 or 17 digits. Got {len(nid)} digits.",
        })

    record = db.query(NIDRecord).filter_by(nid_number=nid).first()

    if not record:
        _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify", "NOT_FOUND")
        raise HTTPException(status_code=404, detail={
            "error_code": "EC_NOT_FOUND",
            "message":    "NID not found in Election Commission database",
            "nid_number": nid,
            "timestamp":  _now(),
        })

    if record.status == "BLOCKED":
        _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify", "BLOCKED")
        raise HTTPException(status_code=403, detail={
            "error_code": "NID_BLOCKED",
            "message":    "This NID has been blocked by the Election Commission",
            "nid_number": nid,
            "timestamp":  _now(),
        })

    _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify", "FOUND")
    log.info("[VERIFY] OK  institution=%s nid=***%s", token_info["institution_id"], nid[-4:])

    return NIDVerifyResponse(
        success=True,
        nid_number=nid,
        session_id=req.session_id,
        source="EC_FAKE_TEST",
        verified_at=_now(),
        bfiu_ref="BFIU Circular No. 29 — Section 3.3",
        data=NIDRecordOut.model_validate(record),
    )


@app.post(
    "/api/v1/verify/dob",
    tags=["Verify"],
    summary="Verify NID + Date of Birth (stricter check)",
    responses={
        200: {"description": "NID + DOB verified"},
        401: {"description": "Invalid token"},
        403: {"description": "NID blocked"},
        404: {"description": "NID not found"},
        422: {"description": "Invalid format or DOB mismatch"},
    },
)
def verify_nid_dob(
    req:        NIDVerifyWithDOBRequest,
    token_info: dict = Depends(require_token),
    db:         Session = Depends(get_db),
):
    """
    Verify NID **and** Date of Birth together.

    More secure than NID-only lookup — requires both fields to match.
    Used in BFIU §3.2 Step 1 (fingerprint/face + NID + DOB flow).
    """
    nid = req.nid_number

    if not _valid_nid(nid):
        raise HTTPException(status_code=422, detail={
            "error_code": "INVALID_NID_FORMAT",
            "message":    "NID must be 10, 13 or 17 digits.",
        })

    record = db.query(NIDRecord).filter_by(nid_number=nid).first()

    if not record:
        _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify/dob", "NOT_FOUND")
        raise HTTPException(status_code=404, detail={
            "error_code": "EC_NOT_FOUND",
            "message":    "NID not found in Election Commission database",
        })

    if record.status == "BLOCKED":
        _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify/dob", "BLOCKED")
        raise HTTPException(status_code=403, detail={
            "error_code": "NID_BLOCKED",
            "message":    "This NID has been blocked",
        })

    if record.date_of_birth != req.date_of_birth:
        _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify/dob", "DOB_MISMATCH")
        raise HTTPException(status_code=422, detail={
            "error_code": "DOB_MISMATCH",
            "message":    "Date of birth does not match EC record",
            "nid_number": nid,
            "timestamp":  _now(),
        })

    _log_audit(db, token_info["institution_id"], nid, "/api/v1/verify/dob", "FOUND")
    return {
        "success":     True,
        "nid_number":  nid,
        "dob_matched": True,
        "session_id":  req.session_id,
        "source":      "EC_FAKE_TEST",
        "verified_at": _now(),
        "bfiu_ref":    "BFIU Circular No. 29 — Section 3.2 Step 1",
        "data":        NIDRecordOut.model_validate(record),
    }


@app.get(
    "/api/v1/verify/{nid_number}",
    tags=["Verify"],
    summary="GET-style NID lookup",
)
def get_nid(
    nid_number: str,
    token_info: dict = Depends(require_token),
    db:         Session = Depends(get_db),
):
    """GET endpoint — some integrations prefer this over POST."""
    nid = nid_number.strip()
    if not _valid_nid(nid):
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_NID_FORMAT"})
    record = db.query(NIDRecord).filter_by(nid_number=nid).first()
    if not record:
        raise HTTPException(status_code=404, detail={"error_code": "EC_NOT_FOUND"})
    if record.status == "BLOCKED":
        raise HTTPException(status_code=403, detail={"error_code": "NID_BLOCKED"})
    _log_audit(db, token_info["institution_id"], nid, "GET /api/v1/verify", "FOUND")
    return {"success": True, "nid_number": nid, "source": "EC_FAKE_TEST",
            "verified_at": _now(), "data": NIDRecordOut.model_validate(record)}


# ── Admin ─────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/nids",
    tags=["Admin"],
    summary="List all seeded NID records",
)
def list_nids(db: Session = Depends(get_db)):
    """Returns all NID records from the PostgreSQL database."""
    records = db.query(NIDRecord).all()
    return {
        "count": len(records),
        "nids": [
            {
                "nid_number":   r.nid_number,
                "full_name_en": r.full_name_en,
                "date_of_birth":r.date_of_birth,
                "gender":       r.gender,
                "district":     r.district,
                "nid_type":     r.nid_type,
                "status":       r.status,
            }
            for r in records
        ],
    }


@app.post(
    "/api/v1/nids",
    tags=["Admin"],
    status_code=201,
    summary="Seed a new NID record into the database",
)
def add_nid(req: NIDSeedRequest, db: Session = Depends(get_db)):
    """Add a custom NID record for testing."""
    if not _valid_nid(req.nid_number.strip()):
        raise HTTPException(status_code=422, detail="Invalid nid_number format")
    if db.query(NIDRecord).filter_by(nid_number=req.nid_number).first():
        raise HTTPException(status_code=409, detail="NID already exists")
    db.add(NIDRecord(**req.model_dump()))
    db.commit()
    return {"seeded": True, "nid_number": req.nid_number}


@app.delete(
    "/api/v1/nids/{nid_number}",
    tags=["Admin"],
    summary="Delete NID record from database",
)
def delete_nid(nid_number: str, db: Session = Depends(get_db)):
    record = db.query(NIDRecord).filter_by(nid_number=nid_number).first()
    if not record:
        raise HTTPException(status_code=404, detail="NID not found")
    db.delete(record)
    db.commit()
    return {"deleted": True, "nid_number": nid_number}


@app.get(
    "/api/v1/audit",
    tags=["Admin"],
    summary="View audit log",
)
def audit_log(limit: int = 50, db: Session = Depends(get_db)):
    """Returns the last N audit log entries (BFIU §4 audit trail)."""
    entries = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return {
        "count": len(entries),
        "entries": [
            {
                "id":             e.id,
                "request_id":     e.request_id,
                "institution_id": e.institution_id,
                "nid_last4":      e.nid_last4,
                "endpoint":       e.endpoint,
                "result":         e.result,
                "reason":         e.reason,
                "requested_at":   e.requested_at.isoformat() if e.requested_at else None,
            }
            for e in entries
        ],
    }
