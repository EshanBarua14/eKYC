"""
M79: Tenant schema auto-provisioning — BFIU Circular No. 29 §5.2
Called on institution onboard. Creates isolated PostgreSQL schema.
Schema name sourced from Institution.schema_name (set during institution creation).
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import _is_postgres

log = logging.getLogger(__name__)
BST = timezone(timedelta(hours=6))

# Strict allowlist pattern — only lowercase letters, digits, underscore
_SCHEMA_PATTERN = re.compile(r'^[a-z][a-z0-9_]{2,62}$')

RESERVED_SCHEMAS = frozenset({
    "public", "pg_catalog", "information_schema",
    "pg_toast", "pg_temp", "admin", "root",
})


def _validate_schema_name(schema_name: str) -> str:
    """Validate schema name — prevent SQL injection and reserved name conflicts."""
    clean = schema_name.strip().lower()
    if not _SCHEMA_PATTERN.match(clean):
        raise ValueError(
            f"Invalid schema name '{clean}'. "
            "Must start with letter, contain only [a-z0-9_], length 3–63."
        )
    if clean in RESERVED_SCHEMAS:
        raise ValueError(f"Schema name '{clean}' is reserved.")
    return clean


def provision_tenant_schema(
    db: Session,
    institution_id: str,
    schema_name: str,
    institution_name: str = "",
) -> dict:
    """
    Create PostgreSQL schema for new institution tenant.
    Idempotent — safe to call multiple times (uses CREATE SCHEMA IF NOT EXISTS).
    BFIU §5.2: complete data isolation between institutions.

    Returns dict with status and schema_name.
    """
    if not _is_postgres:
        log.warning("[M79] Not PostgreSQL — schema provisioning skipped (dev/test mode)")
        return {
            "status": "SKIPPED",
            "reason": "non-postgres",
            "schema_name": schema_name,
            "institution_id": institution_id,
        }

    validated = _validate_schema_name(schema_name)

    try:
        # Check if schema already exists
        result = db.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :s"),
            {"s": validated},
        ).fetchone()

        if result:
            log.info("[M79] Schema '%s' already exists — skipping (idempotent)", validated)
            return {
                "status": "ALREADY_EXISTS",
                "schema_name": validated,
                "institution_id": institution_id,
                "provisioned_at": None,
            }

        # CREATE SCHEMA — safe: validated against strict pattern, not user-interpolated
        db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {validated}"))

        # Grant access to application role if it exists
        try:
            db.execute(text(
                f"GRANT USAGE ON SCHEMA {validated} TO application_role"
            ))
            db.execute(text(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA {validated} "
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO application_role"
            ))
        except Exception as grant_err:
            # application_role may not exist in all environments — non-fatal
            log.warning("[M79] Could not grant privileges on %s: %s", validated, grant_err)

        db.commit()

        bst_now = datetime.now(BST).strftime("%Y-%m-%d %H:%M:%S BST")
        log.info("[M79] Schema '%s' provisioned for institution '%s' (%s) at %s",
                 validated, institution_name, institution_id, bst_now)

        return {
            "status": "CREATED",
            "schema_name": validated,
            "institution_id": institution_id,
            "institution_name": institution_name,
            "provisioned_at": bst_now,
            "bfiu_ref": "BFIU Circular No. 29 §5.2",
        }

    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        log.error("[M79] Schema provisioning failed for '%s': %s", schema_name, e)
        raise RuntimeError(f"Tenant schema provisioning failed: {e}") from e


def deprovision_tenant_schema(
    db: Session,
    schema_name: str,
    institution_id: str,
    cascade: bool = False,
) -> dict:
    """
    Deactivate tenant schema — RENAME only, never DROP (5-year retention §5.1).
    Renames schema to archived_{schema_name}_{timestamp} to prevent accidental access.
    """
    if not _is_postgres:
        return {"status": "SKIPPED", "reason": "non-postgres"}

    validated = _validate_schema_name(schema_name)
    bst_ts = datetime.now(BST).strftime("%Y%m%d%H%M%S")
    archive_name = f"archived_{validated}_{bst_ts}"

    try:
        db.execute(text(f"ALTER SCHEMA {validated} RENAME TO {archive_name}"))
        db.commit()
        log.info("[M79] Schema '%s' archived as '%s' (BFIU §5.1 retention)",
                 validated, archive_name)
        return {
            "status": "ARCHIVED",
            "original_schema": validated,
            "archived_as": archive_name,
            "institution_id": institution_id,
            "bfiu_ref": "BFIU Circular No. 29 §5.1 — 5-year retention",
        }
    except Exception as e:
        db.rollback()
        log.error("[M79] Deprovision failed for '%s': %s", validated, e)
        raise RuntimeError(f"Deprovision failed: {e}") from e


def add_schema_to_allowlist(schema_name: str) -> None:
    """
    Runtime-update the tenant middleware allowlist with the new schema.
    Called after successful provisioning so the middleware accepts it immediately.
    """
    try:
        from app.middleware.tenant_db import _ALLOWED_SCHEMAS
        # frozenset is immutable — swap module-level reference
        import app.middleware.tenant_db as tenant_mod
        current = set(tenant_mod._ALLOWED_SCHEMAS)
        current.add(schema_name.strip().lower())
        tenant_mod._ALLOWED_SCHEMAS = frozenset(current)
        log.info("[M79] Schema '%s' added to middleware allowlist", schema_name)
    except Exception as e:
        log.warning("[M79] Could not update middleware allowlist: %s", e)
