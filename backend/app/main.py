"""
Xpert Fintech eKYC Platform — API Entry Point
BFIU Circular No. 29 Compliant
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.error_boundary import register_error_handlers
from app.api.v1.router import v1_router
from app.db.database import engine, init_db
from app.db import models

# Create all tables on startup (dev) — use Alembic in production
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Xpert Fintech eKYC Platform
**BFIU Circular No. 29 Compliant**

| Module | Endpoint | Status |
|--------|----------|--------|
| Face Verification | POST /api/v1/face/verify | Live |
| AI Analysis | POST /api/v1/ai/analyze | Live |
| Liveness Challenge | POST /api/v1/ai/challenge | Live |
| NID Scan | POST /api/v1/ai/scan-nid | Live |
| KYC Profile | POST /api/v1/kyc/profile | Live |
| Fingerprint | POST /api/v1/fingerprint/verify | Coming |
| Risk Grading | POST /api/v1/risk/grade | Coming |
| Sanctions Screen | POST /api/v1/sanctions/screen 
| Coming |
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Rate Limiting (M28) ────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    print("[M28] Rate limiting enabled")
except ImportError:
    print("[M28] slowapi not installed — rate limiting disabled")
    limiter = None

@app.on_event("startup")
def startup():
    init_db()
    _seed_demo_users()


def _seed_demo_users():
    """Seed in-memory demo users with TOTP on startup — dev mode only."""
    try:
        from app.api.v1.routes.auth import _demo_users, _demo_institution
        from app.db.models.auth import User
        from app.services.auth_service import hash_password

        TOTP_SECRET = "JBSWY3DPEHPK3PXP"

        DEMO_USERS = [
            {"id":"user-0001","email":"agent@demo.ekyc",  "phone":"01700000001","full_name":"Demo Agent",  "role":"AGENT",  "password":"DemoAgent@2026",  "totp":False},
            {"id":"user-0002","email":"admin@demo.ekyc",  "phone":"01700000002","full_name":"Demo Admin",  "role":"ADMIN",  "password":"AdminDemo@2026",  "totp":True},
            {"id":"user-0003","email":"maker@demo.ekyc",  "phone":"01700000003","full_name":"Demo Maker",  "role":"MAKER",  "password":"DemoMaker@2026",  "totp":False},
            {"id":"user-0004","email":"checker@demo.ekyc","phone":"01700000004","full_name":"Demo Checker","role":"CHECKER","password":"DemoChecker@2026","totp":True},
            {"id":"user-0005","email":"auditor@demo.ekyc","phone":"01700000005","full_name":"Demo Auditor","role":"AUDITOR","password":"DemoAudit@2026", "totp":True},
        ]

        existing_emails = {u.email for u in _demo_users}
        for d in DEMO_USERS:
            if d["email"] not in existing_emails:
                user = User(
                    id=d["id"],
                    institution_id=_demo_institution.id,
                    email=d["email"],
                    phone=d["phone"],
                    full_name=d["full_name"],
                    role=d["role"],
                    password_hash=hash_password(d["password"]),
                    totp_secret=TOTP_SECRET if d["totp"] else None,
                    totp_enabled=d["totp"],
                    is_active=True,
                    failed_login_count=0,
                )
                _demo_users.append(user)

        import logging
        logging.getLogger(__name__).info(
            "[startup] Demo users seeded: %s",
            [u.email for u in _demo_users]
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("[startup] Demo user seed failed: %s", exc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.types import ASGIApp, Receive, Scope, Send

class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                raw = list(message.get("headers", []))
                raw += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]
                message["headers"] = raw
            await send(message)
        await self.app(scope, receive, send_with_headers)

app.add_middleware(SecurityHeadersMiddleware)
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

# ── Error Boundary (M30) ─────────────────────────────────────────────────
register_error_handlers(app)

@app.get("/health", tags=["System"])
async def health():
    from datetime import datetime, timezone
    from sqlalchemy import text
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return {
        "status":    "healthy" if db_ok else "degraded",
        "db":        "ok" if db_ok else "error",
        "service":   settings.APP_NAME,
        "version":   settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bfiu_ref":  "BFIU Circular No. 29",
        "modules":   ["face_verify","ai_analysis","liveness","kyc_profile",
                      "consent","outcome","fallback","screening","admin"],
    }

# ── Serve uploaded files (NID images, signatures, photos) ─────────────────
import os as _os
_UPLOAD_DIR = _os.path.join(_os.path.dirname(__file__), "../uploads")
_os.makedirs(_UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=_UPLOAD_DIR), name="uploads")
    print(f"[M27] File storage mounted at /uploads → {_UPLOAD_DIR}")
except Exception as _e:
    print(f"[M27] Static files warning: {_e}")