"""M62: Add pep_entries, pep_list_meta, pep_audit_log tables
BFIU Circular No. 29 §4.2 — PEP/IP DB

Revision ID: m62_pep_tables
Revises: m60_edd_workflow
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m62_pep_tables"
down_revision = "m60_edd_workflow"
branch_labels = None
depends_on = None


def upgrade():
    # ── pep_entries ───────────────────────────────────────────────────────
    op.create_table("pep_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name_en", sa.String(255), nullable=False),
        sa.Column("full_name_bn", sa.String(255), nullable=True),
        sa.Column("aliases", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("date_of_birth", sa.String(10), nullable=True),
        sa.Column("national_id", sa.String(64), nullable=True),
        sa.Column("passport_number", sa.String(32), nullable=True),
        sa.Column("nationality", sa.String(3), nullable=False, server_default="BD"),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("position", sa.String(255), nullable=True),
        sa.Column("ministry_or_org", sa.String(255), nullable=True),
        sa.Column("country", sa.String(3), nullable=False, server_default="BD"),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="HIGH"),
        sa.Column("edd_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("status", sa.String(10), nullable=False, server_default="ACTIVE"),
        sa.Column("source", sa.String(64), nullable=False, server_default="MANUAL"),
        sa.Column("source_reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("added_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deactivated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("category IN ('PEP','IP','PEP_FAMILY','PEP_ASSOCIATE')", name="ck_pep_entries_category"),
        sa.CheckConstraint("status IN ('ACTIVE','INACTIVE','DECEASED')", name="ck_pep_entries_status"),
        sa.CheckConstraint("risk_level IN ('HIGH','MEDIUM','LOW')", name="ck_pep_entries_risk_level"),
    )
    op.create_index("ix_pep_entries_name_en", "pep_entries", ["full_name_en"])
    op.create_index("ix_pep_entries_name_bn", "pep_entries", ["full_name_bn"])
    op.create_index("ix_pep_entries_category_status", "pep_entries", ["category", "status"])
    op.create_index("ix_pep_entries_national_id", "pep_entries", ["national_id"])
    op.create_index("ix_pep_entries_status", "pep_entries", ["status"])

    # ── pep_list_meta ──────────────────────────────────────────────────────
    op.create_table("pep_list_meta",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("list_name", sa.String(64), nullable=False, unique=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("total_entries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bfiu_ref", sa.String(128), nullable=False, server_default="BFIU Circular No. 29 §4.2"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── pep_audit_log ──────────────────────────────────────────────────────
    op.create_table("pep_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("pep_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("before_state", postgresql.JSONB, nullable=True),
        sa.Column("after_state", postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_pep_audit_log_entry_id", "pep_audit_log", ["pep_entry_id"])
    op.create_index("ix_pep_audit_log_created", "pep_audit_log", ["created_at"])
    op.create_index("ix_pep_audit_log_action", "pep_audit_log", ["action"])

    # ── Immutability trigger on pep_audit_log (BFIU §5.1) ─────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_pep_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'pep_audit_log is append-only. % not permitted. BFIU §5.1', TG_OP;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER enforce_pep_audit_immutability
            BEFORE UPDATE OR DELETE ON pep_audit_log
            FOR EACH ROW EXECUTE FUNCTION prevent_pep_audit_modification();
    """)

    # ── Seed initial list meta ─────────────────────────────────────────────
    op.execute("""
        INSERT INTO pep_list_meta (id, list_name, version, total_entries, bfiu_ref)
        VALUES (gen_random_uuid(), 'BFIU_PEP_IP', '1.0', 0, 'BFIU Circular No. 29 §4.2')
        ON CONFLICT (list_name) DO NOTHING;
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS enforce_pep_audit_immutability ON pep_audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_pep_audit_modification()")
    op.drop_table("pep_audit_log")
    op.drop_table("pep_list_meta")
    op.drop_table("pep_entries")
