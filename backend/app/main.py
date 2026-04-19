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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

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