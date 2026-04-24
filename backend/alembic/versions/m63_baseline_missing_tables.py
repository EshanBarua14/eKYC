"""M63: Baseline migration — register existing tables under Alembic control.
Tables were previously created via create_all(). This migration makes Alembic
the sole authority. Uses CREATE TABLE IF NOT EXISTS so safe to run on fresh DB.

Revision ID: m63_baseline_missing_tables
Revises: m62_pep_tables
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m63_baseline_missing_tables"
down_revision = "m62_pep_tables"
branch_labels = None
depends_on = None


def upgrade():
    """
    Register all tables that were created via create_all() into Alembic.
    Uses IF NOT EXISTS — safe on both fresh and existing DBs.
    """
    conn = op.get_bind()

    # ── audit_logs ────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(64) NOT NULL,
            user_id UUID,
            user_role VARCHAR(16),
            ip_address INET,
            session_id VARCHAR(128),
            entity_type VARCHAR(64) NOT NULL,
            entity_id UUID,
            before_state JSONB,
            after_state JSONB,
            metadata JSONB,
            bfiu_ref VARCHAR(128),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── kyc_profiles ──────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS kyc_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(128),
            agent_id VARCHAR(64),
            kyc_type VARCHAR(16) NOT NULL DEFAULT 'SIMPLIFIED',
            nid_hash VARCHAR(64),
            full_name_en VARCHAR(255),
            full_name_bn VARCHAR(255),
            date_of_birth VARCHAR(10),
            father_name VARCHAR(255),
            mother_name VARCHAR(255),
            spouse_name VARCHAR(255),
            present_address TEXT,
            permanent_address TEXT,
            mobile VARCHAR(20),
            email VARCHAR(320),
            profession VARCHAR(128),
            monthly_income NUMERIC(15,2),
            source_of_funds VARCHAR(255),
            nationality VARCHAR(3) DEFAULT 'BD',
            nrb_flag BOOLEAN DEFAULT FALSE,
            nominee_name VARCHAR(255),
            nominee_relation VARCHAR(64),
            signature_data TEXT,
            pep_flag BOOLEAN DEFAULT FALSE,
            risk_score INTEGER DEFAULT 0,
            risk_level VARCHAR(10) DEFAULT 'LOW',
            adverse_media_flag BOOLEAN DEFAULT FALSE,
            adverse_media_last_checked TIMESTAMP WITH TIME ZONE,
            workflow_type VARCHAR(16) DEFAULT 'SIMPLIFIED',
            status VARCHAR(20) DEFAULT 'PENDING',
            bfiu_ref VARCHAR(128) DEFAULT 'BFIU Circular No. 29',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── consent_records ───────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS consent_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(128),
            agent_id VARCHAR(64),
            customer_nid_hash VARCHAR(64),
            consent_type VARCHAR(32) NOT NULL,
            consent_given BOOLEAN NOT NULL DEFAULT FALSE,
            ip_address INET,
            device_info JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── onboarding_outcomes ───────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS onboarding_outcomes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(128),
            agent_id VARCHAR(64),
            kyc_type VARCHAR(16),
            outcome VARCHAR(20) NOT NULL,
            risk_level VARCHAR(10),
            pep_flag BOOLEAN DEFAULT FALSE,
            unscr_flag BOOLEAN DEFAULT FALSE,
            edd_required BOOLEAN DEFAULT FALSE,
            edd_case_id UUID,
            decision_reason TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── fallback_cases ────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS fallback_cases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(128),
            agent_id VARCHAR(64),
            customer_nid_hash VARCHAR(64),
            fallback_reason VARCHAR(64) NOT NULL,
            attempts_made INTEGER DEFAULT 0,
            pep_flag BOOLEAN DEFAULT FALSE,
            status VARCHAR(20) DEFAULT 'OPEN',
            resolved_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── bo_accounts ───────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS bo_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kyc_profile_id UUID,
            account_number VARCHAR(64),
            account_type VARCHAR(32),
            institution_id UUID,
            pep_flag BOOLEAN DEFAULT FALSE,
            risk_level VARCHAR(10) DEFAULT 'LOW',
            status VARCHAR(20) DEFAULT 'ACTIVE',
            opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── bo_declarations ───────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS bo_declarations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kyc_profile_id UUID,
            declaration_type VARCHAR(32) NOT NULL,
            declared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            content JSONB,
            signature_data TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── beneficial_owners ─────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS beneficial_owners (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kyc_profile_id UUID,
            full_name_en VARCHAR(255),
            full_name_bn VARCHAR(255),
            nid_hash VARCHAR(64),
            ownership_type VARCHAR(32),
            ownership_percentage NUMERIC(5,2),
            is_pep BOOLEAN DEFAULT FALSE,
            nationality VARCHAR(3) DEFAULT 'BD',
            date_of_birth VARCHAR(10),
            address TEXT,
            source_of_funds VARCHAR(255),
            status VARCHAR(20) DEFAULT 'ACTIVE',
            bfiu_ref VARCHAR(128) DEFAULT 'BFIU Circular No. 29 §4.2',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── notification_logs ─────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS notification_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(128),
            recipient_mobile VARCHAR(20),
            recipient_email VARCHAR(320),
            notification_type VARCHAR(32) NOT NULL,
            channel VARCHAR(10) NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING',
            sent_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── bfiu_reports ──────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS bfiu_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_type VARCHAR(32) NOT NULL,
            period_start TIMESTAMP WITH TIME ZONE,
            period_end TIMESTAMP WITH TIME ZONE,
            generated_by UUID,
            status VARCHAR(20) DEFAULT 'DRAFT',
            content JSONB,
            file_path VARCHAR(512),
            bfiu_ref VARCHAR(128) DEFAULT 'BFIU Circular No. 29',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── unscr_entries ─────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS unscr_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            un_reference_number VARCHAR(64) UNIQUE,
            full_name VARCHAR(512) NOT NULL,
            aliases JSONB DEFAULT '[]',
            entity_type VARCHAR(16) DEFAULT 'INDIVIDUAL',
            nationality VARCHAR(3),
            date_of_birth VARCHAR(10),
            passport_numbers JSONB DEFAULT '[]',
            listing_reason TEXT,
            committee VARCHAR(64),
            listed_at TIMESTAMP WITH TIME ZONE,
            delisted_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT TRUE,
            name_tsvector TSVECTOR,
            bfiu_ref VARCHAR(128) DEFAULT 'BFIU Circular No. 29 §3.2.2',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── unscr_list_meta ───────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS unscr_list_meta (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            list_name VARCHAR(64) UNIQUE NOT NULL,
            version VARCHAR(32),
            total_entries INTEGER DEFAULT 0,
            last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            source_url VARCHAR(512),
            bfiu_ref VARCHAR(128) DEFAULT 'BFIU Circular No. 29 §3.2.2',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── uploaded_files ────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(128),
            file_type VARCHAR(32) NOT NULL,
            file_name VARCHAR(255),
            file_path VARCHAR(512),
            file_size INTEGER,
            mime_type VARCHAR(64),
            uploaded_by UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── webhooks ──────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            institution_id UUID,
            event_type VARCHAR(64) NOT NULL,
            url VARCHAR(512) NOT NULL,
            secret_hash VARCHAR(256),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))

    # ── webhook_deliveries ────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            webhook_id UUID,
            event_type VARCHAR(64),
            payload JSONB,
            status VARCHAR(20) DEFAULT 'PENDING',
            response_code INTEGER,
            response_body TEXT,
            attempts INTEGER DEFAULT 0,
            delivered_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))


def downgrade():
    # Only drop if explicitly rolling back M63
    # Do NOT drop tables that had data before M63
    pass
