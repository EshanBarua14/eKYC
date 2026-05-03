"""
Fake EC NID Verification API — Router
Mounted inside the main eKYC app so endpoints appear in localhost:8000/docs.

Tag : "🔴 EC NID Database (Fake / Test)"
Prefix: /ec

Endpoints visible in Swagger:
  POST /api/v1/ec/auth
  POST /api/v1/ec/verify
  POST /api/v1/ec/verify/dob
  GET  /api/v1/ec/verify/{nid}
  GET  /api/v1/ec/nids
  POST /api/v1/ec/nids
  DELETE /api/v1/ec/nids/{nid}
  GET  /api/v1/ec/audit
  GET  /api/v1/ec/status
"""

import re
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

log = logging.getLogger("fake_ec_router")

# ── Separate DB connection to fake_ec_db ─────────────────────────────────
import os
_FAKE_EC_DB_URL = os.getenv(
    "FAKE_EC_DB_URL",
    "postgresql://ec_api_user:ec_api_pass_2026@localhost:5432/fake_ec_db"
)
try:
    _engine = create_engine(_FAKE_EC_DB_URL, pool_pre_ping=True, echo=False)
    _Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    _db_available = True
except Exception:
    _db_available = False

_Base = declarative_base()

class _NIDRecord(_Base):
    __tablename__ = "nid_records"
    nid_number        = Column(String(20),  primary_key=True)
    smart_card_number = Column(String(30),  nullable=True)
    pin               = Column(String(20),  nullable=True)
    full_name_en      = Column(String(200), nullable=False)
    full_name_bn      = Column(String(200), nullable=False)
    date_of_birth     = Column(String(10),  nullable=False)
    fathers_name_en   = Column(String(200), nullable=True)
    fathers_name_bn   = Column(String(200), nullable=True)
    mothers_name_en   = Column(String(200), nullable=True)
    mothers_name_bn   = Column(String(200), nullable=True)
    spouse_name_en    = Column(String(200), nullable=True)
    spouse_name_bn    = Column(String(200), nullable=True)
    present_address   = Column(Text,        nullable=True)
    permanent_address = Column(Text,        nullable=True)
    place_of_birth    = Column(String(100), nullable=True)
    district          = Column(String(100), nullable=True)
    division          = Column(String(100), nullable=True)
    blood_group       = Column(String(5),   nullable=True)
    gender            = Column(String(1),   nullable=False)
    nationality       = Column(String(50),  nullable=True)
    religion          = Column(String(50),  nullable=True)
    occupation        = Column(String(100), nullable=True)
    education         = Column(String(100), nullable=True)
    issue_date        = Column(String(10),  nullable=True)
    expiry_date       = Column(String(10),  nullable=True)
    photo_url         = Column(String(500), nullable=True)
    nid_type          = Column(String(20),  nullable=True)
    status            = Column(String(20),  nullable=False, default="ACTIVE")
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class _Institution(_Base):
    __tablename__ = "ec_institutions"
    client_id     = Column(String(100), primary_key=True)
    client_secret = Column(String(200), nullable=False)
    name          = Column(String(200), nullable=False)
    status        = Column(String(20),  nullable=False)
    scope         = Column(String(200), nullable=False)

class _AuditLog(_Base):
    __tablename__ = "ec_audit_log"
    id             = Column(Integer,     primary_key=True, autoincrement=True)
    request_id     = Column(String(50),  nullable=False)
    institution_id = Column(String(100), nullable=False)
    nid_last4      = Column(String(4),   nullable=False)
    endpoint       = Column(String(100), nullable=False)
    result         = Column(String(20),  nullable=False)
    reason         = Column(String(200), nullable=True)
    requested_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

def _get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()

# ── In-memory token store ─────────────────────────────────────────────────
_tokens: dict = {}
TOKEN_TTL = 3600
_security = HTTPBearer()

# ── Helpers ───────────────────────────────────────────────────────────────
def _now(): return datetime.now(timezone.utc).isoformat()
def _valid_nid(n): return bool(re.fullmatch(r"\d{10}|\d{13}|\d{17}", n.strip()))

def _require_token(creds: Annotated[HTTPAuthorizationCredentials, Depends(_security)]) -> dict:
    info = _tokens.get(creds.credentials)
    if not info:
        raise HTTPException(status_code=401, detail={"error_code": "EC_AUTH_ERROR",
            "message": "Invalid token. Call POST /api/v1/ec/auth first."})
    if time.time() > info["exp"]:
        del _tokens[creds.credentials]
        raise HTTPException(status_code=401, detail={"error_code": "EC_AUTH_ERROR",
            "message": "Token expired."})
    return info

def _log_audit(db, institution_id, nid, endpoint, result):
    db.add(_AuditLog(request_id=str(uuid.uuid4())[:8], institution_id=institution_id,
                     nid_last4=nid[-4:], endpoint=endpoint, result=result))
    db.commit()

# ── Schemas ───────────────────────────────────────────────────────────────
class ECAuthRequest(BaseModel):
    client_id:     str = Field(..., example="inst_xpert_001")
    client_secret: str = Field(..., example="sk_test_xpert_ekyc_secret_2026")
    model_config = {"json_schema_extra": {"example": {
        "client_id": "inst_xpert_001",
        "client_secret": "sk_test_xpert_ekyc_secret_2026"}}}

class ECVerifyRequest(BaseModel):
    nid_number: str = Field(..., example="2375411929",
                            description="10, 13 or 17 digit BD NID number")
    session_id: Optional[str] = Field(None, example="sess_20260503_abc123")
    @field_validator("nid_number")
    @classmethod
    def clean(cls, v): return v.strip().replace(" ", "").replace("-", "")
    model_config = {"json_schema_extra": {"example": {
        "nid_number": "2375411929", "session_id": "sess_20260503_abc123"}}}

class ECVerifyDOBRequest(BaseModel):
    nid_number:    str = Field(..., example="2375411929")
    date_of_birth: str = Field(..., example="1994-08-14", description="YYYY-MM-DD")
    session_id:    Optional[str] = None
    @field_validator("nid_number")
    @classmethod
    def clean(cls, v): return v.strip().replace(" ", "").replace("-", "")
    @field_validator("date_of_birth")
    @classmethod
    def valid_dob(cls, v):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
            raise ValueError("Must be YYYY-MM-DD")
        return v.strip()
    model_config = {"json_schema_extra": {"example": {
        "nid_number": "2375411929", "date_of_birth": "1994-08-14"}}}

class ECNIDSeedRequest(BaseModel):
    nid_number:      str
    full_name_en:    str
    full_name_bn:    str
    date_of_birth:   str
    gender:          str
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

def _record_to_dict(r: _NIDRecord) -> dict:
    return {k: getattr(r, k) for k in [
        "nid_number","smart_card_number","pin","full_name_en","full_name_bn",
        "date_of_birth","fathers_name_en","fathers_name_bn","mothers_name_en",
        "mothers_name_bn","spouse_name_en","spouse_name_bn","present_address",
        "permanent_address","place_of_birth","district","division","blood_group",
        "gender","nationality","religion","occupation","education","issue_date",
        "expiry_date","photo_url","nid_type","status"]}

# ── Router ────────────────────────────────────────────────────────────────
router = APIRouter(
    prefix="/ec",
    tags=["🔴 EC NID Database (Fake / Test)"],
)

# ── Status ────────────────────────────────────────────────────────────────
@router.get("/status", summary="Fake EC API status + NID record counts")
def ec_status(db: Session = Depends(_get_db)):
    """Shows how many NID records are in the fake EC PostgreSQL database."""
    total   = db.query(_NIDRecord).count()
    active  = db.query(_NIDRecord).filter_by(status="ACTIVE").count()
    blocked = db.query(_NIDRecord).filter_by(status="BLOCKED").count()
    return {"status": "OPERATIONAL", "version": "1.0.0-fake", "environment": "TEST",
            "nid_records": {"total": total, "active": active, "blocked": blocked},
            "active_tokens": len(_tokens), "timestamp": _now(),
            "note": "Fake EC API — development use only"}

# ── Auth ──────────────────────────────────────────────────────────────────
@router.post(
    "/auth",
    summary="Get Bearer token (institution login)",
    responses={
        200: {"description": "Token issued"},
        401: {"description": "Invalid credentials → EC_AUTH_ERROR"},
        403: {"description": "Institution suspended → INSTITUTION_SUSPENDED"},
    },
)
def ec_auth(req: ECAuthRequest, db: Session = Depends(_get_db)):
    """
    Authenticate an institution and receive a Bearer token.

    **Test credentials:**
    - `inst_xpert_001` / `sk_test_xpert_ekyc_secret_2026`
    - `inst_test_bank` / `sk_test_bank_secret_2026`

    Use the returned `access_token` in the 🔒 Authorize button above,
    then call any `/ec/verify` endpoint.
    """
    inst = db.query(_Institution).filter_by(client_id=req.client_id).first()
    if not inst or inst.client_secret != req.client_secret:
        raise HTTPException(status_code=401, detail={
            "error_code": "EC_AUTH_ERROR", "message": "Invalid client_id or client_secret"})
    if inst.status == "suspended":
        raise HTTPException(status_code=403, detail={
            "error_code": "INSTITUTION_SUSPENDED", "message": "Institution account suspended"})
    token = f"ec_{uuid.uuid4().hex}"
    _tokens[token] = {"institution_id": inst.client_id, "exp": time.time() + TOKEN_TTL}
    return {"access_token": token, "token_type": "Bearer", "expires_in": TOKEN_TTL,
            "scope": inst.scope, "institution_name": inst.name, "issued_at": _now()}

# ── Verify ────────────────────────────────────────────────────────────────
@router.post(
    "/verify",
    summary="Verify NID → returns full citizen record from EC database",
    responses={
        200: {"description": "NID found — full citizen record returned"},
        401: {"description": "Invalid token → EC_AUTH_ERROR"},
        403: {"description": "NID is blocked → NID_BLOCKED"},
        404: {"description": "NID not found → EC_NOT_FOUND"},
        422: {"description": "Invalid NID format → INVALID_NID_FORMAT"},
    },
)
def ec_verify(
    req:        ECVerifyRequest,
    token_info: dict = Depends(_require_token),
    db:         Session = Depends(_get_db),
):
    """
    Main NID verification endpoint — mirrors real Bangladesh EC API.

    Looks up the NID in the **fake EC PostgreSQL database** and returns
    the full citizen record including name (EN+BN), DOB, parents, address,
    blood group, gender, occupation.

    **Seeded test NIDs:**

    | NID | Name |
    |-----|------|
    | `2375411929` | ESHAN BARUA |
    | `19858524905063671` | MD ABUL MOSHAD CHOWDHURY |
    | `1234567890123` | RAHMAN HOSSAIN CHOWDHURY |
    | `9876543210987` | FATEMA BEGUM |
    | `1111111111111` | KARIM UDDIN AHMED |
    | `2222222222222` | NASRIN SULTANA |
    | `3333333333333` | MOHAMMAD RAFIQUL ISLAM |
    | `4444444444444` | SHIRIN AKTER |
    | `0000000000000` | BLOCKED → returns 403 |

    *BFIU Circular No. 29 — Section 3.3*
    """
    nid = req.nid_number
    if not _valid_nid(nid):
        raise HTTPException(status_code=422, detail={
            "error_code": "INVALID_NID_FORMAT",
            "message": f"NID must be 10, 13 or 17 digits. Got: {len(nid)} digits."})
    record = db.query(_NIDRecord).filter_by(nid_number=nid).first()
    if not record:
        _log_audit(db, token_info["institution_id"], nid, "POST /ec/verify", "NOT_FOUND")
        raise HTTPException(status_code=404, detail={
            "error_code": "EC_NOT_FOUND",
            "message": "NID not found in Election Commission database",
            "nid_number": nid, "timestamp": _now()})
    if record.status == "BLOCKED":
        _log_audit(db, token_info["institution_id"], nid, "POST /ec/verify", "BLOCKED")
        raise HTTPException(status_code=403, detail={
            "error_code": "NID_BLOCKED",
            "message": "This NID has been blocked by the Election Commission"})
    _log_audit(db, token_info["institution_id"], nid, "POST /ec/verify", "FOUND")
    return {"success": True, "nid_number": nid, "session_id": req.session_id,
            "source": "EC_FAKE_TEST", "verified_at": _now(),
            "bfiu_ref": "BFIU Circular No. 29 — Section 3.3",
            "data": _record_to_dict(record)}

@router.post(
    "/verify/dob",
    summary="Verify NID + Date of Birth (stricter — both must match)",
    responses={
        200: {"description": "NID + DOB verified"},
        422: {"description": "DOB mismatch → DOB_MISMATCH"},
    },
)
def ec_verify_dob(
    req:        ECVerifyDOBRequest,
    token_info: dict = Depends(_require_token),
    db:         Session = Depends(_get_db),
):
    """
    Verify NID **and** Date of Birth.

    Both the NID number and DOB must match the EC database record.
    More secure than NID-only lookup.

    *BFIU Circular No. 29 — Section 3.2 Step 1*
    """
    nid = req.nid_number
    if not _valid_nid(nid):
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_NID_FORMAT"})
    record = db.query(_NIDRecord).filter_by(nid_number=nid).first()
    if not record:
        raise HTTPException(status_code=404, detail={"error_code": "EC_NOT_FOUND"})
    if record.status == "BLOCKED":
        raise HTTPException(status_code=403, detail={"error_code": "NID_BLOCKED"})
    if record.date_of_birth != req.date_of_birth:
        _log_audit(db, token_info["institution_id"], nid, "POST /ec/verify/dob", "DOB_MISMATCH")
        raise HTTPException(status_code=422, detail={
            "error_code": "DOB_MISMATCH",
            "message": "Date of birth does not match EC record"})
    _log_audit(db, token_info["institution_id"], nid, "POST /ec/verify/dob", "FOUND")
    return {"success": True, "nid_number": nid, "dob_matched": True,
            "session_id": req.session_id, "source": "EC_FAKE_TEST",
            "verified_at": _now(),
            "bfiu_ref": "BFIU Circular No. 29 — Section 3.2 Step 1",
            "data": _record_to_dict(record)}

@router.get("/verify/{nid_number}", summary="GET-style NID lookup")
def ec_get_nid(
    nid_number: str,
    token_info: dict = Depends(_require_token),
    db:         Session = Depends(_get_db),
):
    nid = nid_number.strip()
    if not _valid_nid(nid):
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_NID_FORMAT"})
    record = db.query(_NIDRecord).filter_by(nid_number=nid).first()
    if not record:
        raise HTTPException(status_code=404, detail={"error_code": "EC_NOT_FOUND"})
    if record.status == "BLOCKED":
        raise HTTPException(status_code=403, detail={"error_code": "NID_BLOCKED"})
    return {"success": True, "nid_number": nid, "source": "EC_FAKE_TEST",
            "verified_at": _now(), "data": _record_to_dict(record)}

# ── Admin ─────────────────────────────────────────────────────────────────
@router.get("/nids", summary="List all NID records in the fake EC database")
def ec_list_nids(db: Session = Depends(_get_db)):
    """Returns all seeded NID records from the fake EC PostgreSQL database."""
    records = db.query(_NIDRecord).all()
    return {"count": len(records), "nids": [
        {"nid_number": r.nid_number, "full_name_en": r.full_name_en,
         "date_of_birth": r.date_of_birth, "gender": r.gender,
         "district": r.district, "nid_type": r.nid_type, "status": r.status}
        for r in records]}

@router.post("/nids", status_code=201, summary="Seed a new NID record into the fake EC database")
def ec_add_nid(req: ECNIDSeedRequest, db: Session = Depends(_get_db)):
    """Add a custom NID record for testing purposes."""
    if not _valid_nid(req.nid_number.strip()):
        raise HTTPException(status_code=422, detail="Invalid nid_number format")
    if db.query(_NIDRecord).filter_by(nid_number=req.nid_number).first():
        raise HTTPException(status_code=409, detail="NID already exists")
    db.add(_NIDRecord(**req.model_dump()))
    db.commit()
    return {"seeded": True, "nid_number": req.nid_number}

@router.delete("/nids/{nid_number}", summary="Delete NID record from fake EC database")
def ec_delete_nid(nid_number: str, db: Session = Depends(_get_db)):
    record = db.query(_NIDRecord).filter_by(nid_number=nid_number).first()
    if not record:
        raise HTTPException(status_code=404, detail="NID not found")
    db.delete(record)
    db.commit()
    return {"deleted": True, "nid_number": nid_number}

@router.get("/audit", summary="View fake EC audit log (BFIU §4 audit trail)")
def ec_audit(limit: int = 50, db: Session = Depends(_get_db)):
    """Returns the last N audit log entries from the fake EC database."""
    entries = db.query(_AuditLog).order_by(_AuditLog.id.desc()).limit(limit).all()
    return {"count": len(entries), "entries": [
        {"id": e.id, "request_id": e.request_id, "institution_id": e.institution_id,
         "nid_last4": e.nid_last4, "endpoint": e.endpoint, "result": e.result,
         "requested_at": e.requested_at.isoformat() if e.requested_at else None}
        for e in entries]}
