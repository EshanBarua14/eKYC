"""M41 -- Redis production setup tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_redis_url_configured():
    import os
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    assert url.startswith("redis://")

def test_T02_session_limiter_importable():
    from app.services.session_limiter import hash_nid, gate_attempt
    assert callable(hash_nid)
    assert callable(gate_attempt)

def test_T03_hash_nid_deterministic():
    from app.services.session_limiter import hash_nid
    assert hash_nid("1234567890") == hash_nid("1234567890")

def test_T04_hash_nid_different_inputs():
    from app.services.session_limiter import hash_nid
    assert hash_nid("1234567890") != hash_nid("0987654321")

def test_T05_gate_attempt_returns_dict():
    from app.services.session_limiter import gate_attempt
    r = gate_attempt("1234567890", "test-session")
    assert "allowed" in r

def test_T06_redis_url_in_config():
    from app.core.config import settings
    assert settings.REDIS_URL.startswith("redis://")
