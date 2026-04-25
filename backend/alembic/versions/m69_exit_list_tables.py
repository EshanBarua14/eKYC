"""M69: Add exit_list_entries and exit_list_audit_log tables
BFIU Circular No. 29 §5.1 — institution internal blacklist

Revision ID: m69_exit_list_tables
Revises: m64_audit_immutability
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m69_exit_list_tables"
down_revision = "m64_audit_immutability"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("exit_list_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institution_id", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("name_normalised", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("nid_hash", sa.String(64), nullable=True),
        sa.Column("additional_info", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("added_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("added_by_role", sa.String(32), nullable=True),
        sa.Column("deactivated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deactivated_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_exit_list_institution_id", "exit_list_entries", ["institution_id"])
    op.create_index("ix_exit_list_institution_active", "exit_list_entries", ["institution_id", "is_active"])
    op.create_index("ix_exit_list_name_normalised", "exit_list_entries", ["name_normalised"])
    op.create_index("ix_exit_list_nid_hash", "exit_list_entries", ["nid_hash"])

    op.create_table("exit_list_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("institution_id", sa.String(64), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_exit_list_audit_entry_id", "exit_list_audit_log", ["entry_id"])
    op.create_index("ix_exit_list_audit_institution", "exit_list_audit_log", ["institution_id"])

    # Immutability trigger on audit log (BFIU §5.1)
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_exit_list_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'exit_list_audit_log is append-only. % not permitted. BFIU Circular No. 29 §5.1', TG_OP;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER enforce_exit_list_audit_immutability
            BEFORE UPDATE OR DELETE ON exit_list_audit_log
            FOR EACH ROW EXECUTE FUNCTION prevent_exit_list_audit_modification();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS enforce_exit_list_audit_immutability ON exit_list_audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_exit_list_audit_modification()")
    op.drop_table("exit_list_audit_log")
    op.drop_table("exit_list_entries")
