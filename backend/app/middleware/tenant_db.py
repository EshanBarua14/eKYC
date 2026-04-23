"""
M55 — Tenant Schema Middleware — BFIU Circular No. 29 §5.2
FastAPI dependency that sets PostgreSQL search_path per tenant
extracted from JWT claim 'tenant_schema'.
Replaces get_db() for all routes requiring tenant isolation.
"""
from __future__ import annotations
import logging
from typing import Generator
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal, _is_postgres

log = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)

_ALLOWED_SCHEMAS = frozenset({
    "public", "tenant_demo", "tenant_default",
    "tenant_bank", "tenant_ngo", "tenant_mfi",
    "tenant_nbfi", "tenant_cooperative", "tenant_leasing",
})


def _safe_schema(schema: str | None) -> str:
    """Validate schema name against allowlist — prevent SQL injection."""
    if not schema:
        return "public"
    clean = schema.strip().lower()
    if clean not in _ALLOWED_SCHEMAS:
        log.warning("[M55] Unknown tenant schema %r — falling back to public", schema)
        return "public"
    return clean


def get_tenant_schema(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    """Extract tenant_schema from JWT or request state."""
    # Try request state first (set by auth middleware)
    schema = getattr(request.state, "tenant_schema", None)
    if schema:
        return _safe_schema(schema)

    # Try JWT claim
    if credentials:
        try:
            from app.core.security import decode_token
            payload = decode_token(credentials.credentials)
            schema = payload.get("tenant_schema")
            if schema:
                return _safe_schema(schema)
        except Exception:
            pass

    return "public"


def get_tenant_db(
    schema: str = Depends(get_tenant_schema),
) -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields DB session with search_path set to tenant schema.
    Drop-in replacement for get_db() on tenant-aware routes.
    """
    db = SessionLocal()
    try:
        if _is_postgres and schema != "public":
            db.execute(text(f"SET search_path TO {schema}, public"))
            log.debug("[M55] search_path set to %s", schema)
        yield db
    finally:
        db.close()
