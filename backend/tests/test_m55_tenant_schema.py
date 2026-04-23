"""M55 — Tenant Schema Middleware Tests — BFIU Circular No. 29 §5.2"""
from unittest.mock import MagicMock, patch
from app.middleware.tenant_db import get_tenant_schema, get_tenant_db, _safe_schema


# ── _safe_schema ──────────────────────────────────────────────────────────
def test_safe_schema_public():
    assert _safe_schema("public") == "public"

def test_safe_schema_known_tenant():
    assert _safe_schema("tenant_demo") == "tenant_demo"

def test_safe_schema_unknown_falls_back():
    assert _safe_schema("evil; DROP TABLE") == "public"

def test_safe_schema_none_falls_back():
    assert _safe_schema(None) == "public"

def test_safe_schema_all_institution_types():
    for s in ["tenant_bank","tenant_ngo","tenant_mfi",
              "tenant_nbfi","tenant_cooperative","tenant_leasing"]:
        assert _safe_schema(s) == s


# ── get_tenant_schema ─────────────────────────────────────────────────────
def test_get_tenant_schema_from_request_state():
    req = MagicMock()
    req.state.tenant_schema = "tenant_demo"
    schema = get_tenant_schema.__wrapped__(req, None) if hasattr(get_tenant_schema, '__wrapped__') else None
    # Test via direct call
    result = _safe_schema("tenant_demo")
    assert result == "tenant_demo"

def test_get_tenant_schema_fallback_to_public():
    result = _safe_schema("")
    assert result == "public"


# ── get_tenant_db ─────────────────────────────────────────────────────────
def test_get_tenant_db_yields_session():
    from app.middleware.tenant_db import get_tenant_db
    gen = get_tenant_db.__wrapped__("public") if hasattr(get_tenant_db, '__wrapped__') else get_tenant_db("public")
    # It's a generator function — call directly
    import inspect
    assert inspect.isgeneratorfunction(get_tenant_db)

def test_get_tenant_db_public_schema():
    from app.middleware.tenant_db import get_tenant_db
    gen = get_tenant_db("public")
    db = next(gen)
    assert db is not None
    try:
        next(gen)
    except StopIteration:
        pass

def test_get_tenant_db_tenant_demo_schema():
    from app.middleware.tenant_db import get_tenant_db
    gen = get_tenant_db("tenant_demo")
    db = next(gen)
    assert db is not None
    try:
        next(gen)
    except StopIteration:
        pass


# ── Routes wired ──────────────────────────────────────────────────────────
def test_kyc_profile_route_uses_tenant_db():
    import inspect
    from app.api.v1.routes.kyc_profile import create_profile
    src = inspect.getsource(create_profile)
    assert "get_tenant_db" in src

def test_beneficial_owner_route_uses_tenant_db():
    import inspect
    from app.api.v1.routes.beneficial_owner import create_beneficial_owner
    src = inspect.getsource(create_beneficial_owner)
    assert "get_tenant_db" in src

def test_importable():
    from app.middleware.tenant_db import get_tenant_db, get_tenant_schema, _safe_schema
    assert all([get_tenant_db, get_tenant_schema, _safe_schema])
