"""UNSCR full-text search GIN index + tsvector column

Revision ID: 20260424_205733
Revises: 
Create Date: 2026-04-24T20:57:33.090636
"""
from alembic import op
import sqlalchemy as sa

revision = '20260424_205733'
down_revision = 'b5a0d85cccf3'
branch_labels = None
depends_on = None


def upgrade():
    # Add tsvector column for FTS
    op.execute("""
        ALTER TABLE unscr_entries
        ADD COLUMN IF NOT EXISTS search_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', COALESCE(search_vector, ''))) STORED
    """)

    # Create GIN index for fast FTS
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_unscr_entries_search_tsv
        ON unscr_entries USING GIN(search_tsv)
    """)

    # Index on is_active for fast filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_unscr_entries_is_active
        ON unscr_entries(is_active)
        WHERE is_active = TRUE
    """)

    # Index on list_version
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_unscr_entries_list_version
        ON unscr_entries(list_version)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_unscr_entries_search_tsv")
    op.execute("DROP INDEX IF EXISTS idx_unscr_entries_is_active")
    op.execute("DROP INDEX IF EXISTS idx_unscr_entries_list_version")
    op.execute("ALTER TABLE unscr_entries DROP COLUMN IF EXISTS search_tsv")
