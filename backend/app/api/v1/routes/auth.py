"""
Xpert Fintech eKYC Platform
Auth routes - /token, /refresh, /logout, /register, /totp/setup
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from jose import JWTError

from app.core.security import decode_token, Role, has_permission, ROLE_PERMISSIONS
from app.services.twofa_service import check_2fa_compliance, get_2fa_policy
from app.services.auth_service import (
    hash_password, verify_password,
    generate_totp_secret, get_totp_uri, verify_totp, generate_otp,
    issue_token_pair, register_session, revoke_session, is_session_valid,
    check_permission,
)
from app.db.models.auth import Institution, User
from app.middleware.rate_limit_dep import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# ---------------------------------------------------------------------------
# In-memory demo store (SQLite dev mode - replaced by DB in prod)
# ---------------------------------------------------------------------------
_demo_institution = Institution(
    id="inst-demo-001",
    name="Demo Insurance Co.",
    short_code="DEMO",
    institution_type="insurance",
    schema_name="tenant_demo",
    client_id="client_demo_001",
    client_secret_hash="demo",
    ip_whitelist=[],
    status="ACTIVE",
)

_demo_users: list = []

def _get_demo_user(email: str) -> Optional[User]:
    mem = next((u for u in _demo_users if u.email == email), None)
    if mem: return mem
    from app.db.database import SessionLocal
    db = SessionLocal()
    try: return db.query(User).filter_by(email=email).first()
    finally: db.close()

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email:       str
    phone:       str
    full_name:   str
    role:        str
    password:    str
    institution_id: str = "inst-demo-001"

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v):
        valid = [r.value for r in Role]
        if v.upper() not in valid:
            raise ValueError(f"Role must be one of: {valid}")
        return v.upper()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class LoginRequest(BaseModel):
    email:    str
    password: str
    totp_code: Optional[str] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class TOTPVerifyRequest(BaseModel):
    totp_code: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str
    expires_in:    int
    role:          str
    tenant_schema: str

class MessageResponse(BaseModel):
    message: str
    detail:  Optional[str] = None

# ---------------------------------------------------------------------------
# Helper: get current user from Bearer token
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    jti = payload.get("jti", "")
    if not is_session_valid(jti):
        raise HTTPException(status_code=401, detail="Session revoked or expired")

    return payload

# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=MessageResponse, status_code=201)
def register_user(req: RegisterRequest):
    """Register a new staff user. Admin action in production."""
    if _get_demo_user(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")  # checks both mem+DB

    user = User(
        id=str(uuid.uuid4()),
        institution_id=req.institution_id,
        email=req.email,
        phone=req.phone,
        full_name=req.full_name,
        role=req.role,
        password_hash=hash_password(req.password),
        totp_enabled=False,
        is_active=True,
        failed_login_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _demo_users.append(user)
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=req.email).first()
        if not existing:
            db.add(user); db.commit()
    finally: db.close()
    return {"message": "User registered successfully", "detail": f"Role: {req.role}"}

# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------
@router.post("/token", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth_token"))])
def login(req: LoginRequest, request: Request):
    """Issue JWT access + refresh token pair."""
    user = _get_demo_user(req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # ── 2FA enforcement (M32) ────────────────────────────────────────────
    import os
    _demo_mode = os.environ.get("EKYC_DEMO_MODE", "").lower() == "true"
    _skip_2fa = _demo_mode and getattr(user, "institution_id", None) == "inst-bypass-001"
    compliance = {"allowed": True} if _skip_2fa else check_2fa_compliance(
        role=user.role,
        totp_enabled=user.totp_enabled,
        totp_code=req.totp_code,
        totp_secret=user.totp_secret,
    )
    if not compliance["allowed"]:
        raise HTTPException(
            status_code=401,
            detail={
                "error":           compliance.get("error_code","2FA_REQUIRED"),
                "message":         compliance["reason"],
                "action_required": compliance.get("action_required"),
                "bfiu_ref":        "BFIU Circular No. 29 - Section 3.2.5",
            }
        )
    # Verify TOTP code if provided and enabled
    if user.totp_enabled and req.totp_code:
        if not verify_totp(user.totp_secret, req.totp_code):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    tokens = issue_token_pair(
        user=user,
        institution=_demo_institution,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Register session
    from app.core.security import decode_token as _dt
    payload = _dt(tokens["access_token"])
    register_session(
        jti=payload["jti"],
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )

    return tokens

# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest):
    """Issue a new access token using a valid refresh token."""
    try:
        payload = decode_token(req.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = payload.get("user_id")
    user = next((u for u in _demo_users if str(u.id) == str(user_id)), None)
    if not user:
        try:
            from app.db.database import SessionLocal as _SL2
            _db2 = _SL2()
            user = _db2.query(User).filter_by(id=user_id, is_active=True).first()
            _db2.close()
        except Exception:
            pass
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    tokens = issue_token_pair(user=user, institution=_demo_institution)
    payload2 = decode_token(tokens["access_token"])
    register_session(
        jti=payload2["jti"],
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    return tokens

# ---------------------------------------------------------------------------
# DELETE /auth/logout
# ---------------------------------------------------------------------------
@router.delete("/logout", response_model=MessageResponse)
def logout(current_user: dict = Depends(get_current_user)):
    """Revoke current session by jti."""
    jti = current_user.get("jti", "")
    revoke_session(jti)
    return {"message": "Logged out successfully", "detail": f"Session {jti} revoked"}

# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Return current user info from token."""
    role = current_user.get("role", "")
    return {
        "user_id":       current_user.get("user_id"),
        "institution_id": current_user.get("sub"),
        "role":          role,
        "tenant_schema": current_user.get("tenant_schema"),
        "permissions":   ROLE_PERMISSIONS.get(Role(role), []) if role in [r.value for r in Role] else [],
    }

# ---------------------------------------------------------------------------
# POST /auth/totp/setup
# ---------------------------------------------------------------------------
@router.post("/totp/setup")
def setup_totp(current_user: dict = Depends(get_current_user)):
    """Generate TOTP secret and return QR URI."""
    user_id = current_user.get("user_id")
    user = next((u for u in _demo_users if str(u.id) == str(user_id)), None)
    db_user = None
    if not user:
        from app.db.database import SessionLocal
        _db = SessionLocal()
        try: db_user = _db.query(User).filter_by(id=user_id).first()
        finally: _db.close()
    if not user and not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, (user or db_user).email)
    if user:
        user.totp_secret = secret
    if db_user:
        from app.db.database import SessionLocal
        _db = SessionLocal()
        try:
            u = _db.query(User).filter_by(id=user_id).first()
            u.totp_secret = secret; _db.commit()
        finally: _db.close()
    return {
        "totp_secret": secret,
        "totp_uri":    uri,
        "message":     "Scan the URI with Google Authenticator then call /totp/verify",
    }

# ---------------------------------------------------------------------------
# POST /auth/totp/verify
# ---------------------------------------------------------------------------
@router.post("/totp/verify", response_model=MessageResponse)
def verify_totp_setup(
    req: TOTPVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Confirm TOTP setup by verifying first code."""
    user_id = current_user.get("user_id")
    user = next((u for u in _demo_users if str(u.id) == str(user_id)), None)
    if not user:
        from app.db.database import SessionLocal
        _db = SessionLocal()
        try: user = _db.query(User).filter_by(id=user_id).first()
        finally: _db.close()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up. Call /totp/setup first.")
    if not verify_totp(user.totp_secret, req.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    user.totp_enabled = True
    return {"message": "TOTP enabled successfully"}

# ---------------------------------------------------------------------------
# GET /auth/roles  (Admin only)
# ---------------------------------------------------------------------------
@router.get("/roles")
def list_roles(current_user: dict = Depends(get_current_user)):
    """List all roles and their permissions. Admin only."""
    role = current_user.get("role", "")
    if not check_permission(role, "*"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return {
        r.value: ROLE_PERMISSIONS[r] for r in Role
    }
