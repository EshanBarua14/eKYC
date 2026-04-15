"""
Xpert Fintech eKYC Platform — API Entry Point
BFIU Circular No. 29 Compliant
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import v1_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Xpert Fintech eKYC Platform API
**BFIU Circular No. 29 Compliant** — Bangladesh Financial Intelligence Unit

### Available Modules
| Module | Endpoint | Status |
|--------|----------|--------|
| Face Verification | `POST /api/v1/face/verify` | ✅ Live |
| Fingerprint Match | `POST /api/v1/fingerprint/verify` | 🔜 Coming |
| Risk Grading | `POST /api/v1/risk/grade` | 🔜 Coming |
| Sanctions Screen | `POST /api/v1/sanctions/screen` | 🔜 Coming |
| KYC Profile | `POST /api/v1/kyc/profile` | 🔜 Coming |
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register versioned routes
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["System"])
def health():
    return {
        "status":  "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
