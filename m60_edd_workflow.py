"""M60: Add edd_cases and edd_actions tables.
BFIU Circular No. 29 §4.2/§4.3 — EDD workflow.

Revision ID: m60_edd_workflow
Revises: <prev_revision>  # replace with actual last revision
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m60_edd_workflow"
down_revision = None  # SET TO ACTUAL PREVIOUS REVISION
branch_labels = None
depends_on = None


def upgrade():
    # ── edd_cases ────────────────────────────────────────────────────────────
    op.create_table(
        "edd_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_reference", sa.String(32), nullable=False, unique=True),
        sa.Column("kyc_session_id", sa.String(128), nullable=False),
        sa.Column("customer_nid_hash", sa.String(64), nullable=False),
        sa.Column("trigger", sa.String(32), nullable=False),
        sa.Column("trigger_evidence", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("risk_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sla_deadline", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_existing_customer", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("decision_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_role", sa.String(32), nullable=True),
        sa.Column("decision_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW() AT TIME ZONE 'Asia/Dhaka'")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW() AT TIME ZONE 'Asia/Dhaka'")),
        sa.CheckConstraint(
            "trigger IN ('HIGH_RISK_SCORE','PEP_FLAG','ADVERSE_MEDIA',"
            "'RISK_REGRADE','IRREGULAR_ACTIVITY','MANUAL_TRIGGER')",
            name="ck_edd_cases_trigger",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','INFO_REQUESTED','UNDER_REVIEW',"
            "'APPROVED','REJECTED','AUTO_CLOSED','ESCALATED')",
            name="ck_edd_cases_status",
        ),
    )
    op.create_index("ix_edd_cases_case_reference", "edd_cases", ["case_reference"])
    op.create_index("ix_edd_cases_kyc_session_id", "edd_cases", ["kyc_session_id"])
    op.create_index("ix_edd_cases_customer_nid_hash", "edd_cases", ["customer_nid_hash"])
    op.create_index("ix_edd_cases_status", "edd_cases", ["status"])
    op.create_index("ix_edd_cases_assigned", "edd_cases", ["assigned_to_user_id", "status"])
    op.create_index("ix_edd_cases_status_deadline", "edd_cases", ["status", "sla_deadline"])

    # ── edd_actions ──────────────────────────────────────────────────────────
    op.create_table(
        "edd_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW() AT TIME ZONE 'Asia/Dhaka'")),
        sa.ForeignKeyConstraint(["case_id"], ["edd_cases.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_edd_actions_case_id", "edd_actions", ["case_id"])
    op.create_index("ix_edd_actions_action_type", "edd_actions", ["action_type"])
    op.create_index("ix_edd_actions_case_created", "edd_actions", ["case_id", "created_at"])

    # ── Immutability trigger on edd_actions ──────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_edd_action_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'edd_actions is append-only. % is not permitted. BFIU §5.1', TG_OP;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER enforce_edd_action_immutability
            BEFORE UPDATE OR DELETE ON edd_actions
            FOR EACH ROW EXECUTE FUNCTION prevent_edd_action_modification();
    """)

    # ── updated_at trigger on edd_cases ──────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_edd_case_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW() AT TIME ZONE 'Asia/Dhaka';
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER set_edd_case_updated_at
            BEFORE UPDATE ON edd_cases
            FOR EACH ROW EXECUTE FUNCTION update_edd_case_timestamp();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS enforce_edd_action_immutability ON edd_actions")
    op.execute("DROP TRIGGER IF EXISTS set_edd_case_updated_at ON edd_cases")
    op.execute("DROP FUNCTION IF EXISTS prevent_edd_action_modification()")
    op.execute("DROP FUNCTION IF EXISTS update_edd_case_timestamp()")
    op.drop_table("edd_actions")
    op.drop_table("edd_cases")
