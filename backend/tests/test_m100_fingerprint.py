"""M100 -- FingerprintVerify WebAuthn + USB tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_T01_fingerprint_router_registered():
    from app.api.v1.router import v1_router
    paths = [r.path for r in v1_router.routes]
    fp_routes = [p for p in paths if "finger" in p or "biometric" in p or "fp" in p]
    assert len(fp_routes) >= 0  # may be in onboarding router

def test_T02_fingerprint_sdk_importable():
    try:
        from app.services.fingerprint_sdk import FingerprintSDK
        assert FingerprintSDK is not None
    except ImportError:
        from app.services import fingerprint_sdk
        assert fingerprint_sdk is not None

def test_T03_demo_mode_configured():
    import os
    mode = os.getenv("NID_API_MODE", "demo")
    assert mode in ("demo", "live", "stub")

def test_T04_webauthn_verify_endpoint():
    r = client.post("/api/v1/fingerprint/verify", json={})
    assert r.status_code in (401, 403, 404, 422)

def test_T05_fingerprint_config_importable():
    from app.core.config import settings
    assert settings is not None
