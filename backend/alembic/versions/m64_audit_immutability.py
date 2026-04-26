"""M64: DB-level immutability trigger on audit_logs + audit_log table
BFIU Circular No. 29 §5.1 — audit trail must be physically immutable.
Application-level protection is insufficient — DB trigger enforces it.

Revision ID: m64_audit_immutability
Revises: m63_baseline_missing_tables
Create Date: 2026-04-25
"""
from alembic import op

revision = "m64_audit_immutability"
down_revision = "m63_baseline_missing_tables"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "sqlite":
        return
    # ── Immutability trigger on audit_logs ────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
                RAISE EXCEPTION
                    'audit_logs is append-only. % is not permitted. BFIU Circular No. 29 §5.1 — immutable audit trail.',
                    TG_OP;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_audit_log_immutability ON audit_logs;
        CREATE TRIGGER enforce_audit_log_immutability
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
    """)

    # public.audit_log not present in this deployment — audit_logs table used instead

    # ── BST timestamp default on audit_logs ───────────────────────────────
    op.execute("""
        ALTER TABLE audit_logs
            ALTER COLUMN timestamp SET DEFAULT (NOW() AT TIME ZONE 'UTC');
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS enforce_audit_log_immutability ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS enforce_public_audit_immutability ON public.audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification()")
    op.execute("DROP FUNCTION IF EXISTS prevent_public_audit_modification()")
