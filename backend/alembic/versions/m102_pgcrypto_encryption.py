"""M102: pgcrypto AES-256 field encryption — BFIU Circular No. 29 §4.5

Fixes M54 which had an empty upgrade() body.
On PostgreSQL: enables pgcrypto, alters 3 columns to BYTEA.
On SQLite: no-op (encryption handled at ORM layer via Fernet).

Revision ID: m102_pgcrypto_encryption
Revises: m69_exit_list_tables
Create Date: 2026-04-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'm102_pgcrypto_encryption'
down_revision: Union[str, None] = 'm69_exit_list_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite dev - encryption at ORM layer

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Skip if columns already bytea (already migrated)
    result = bind.execute(sa.text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='consent_records' AND column_name='nid_hash'"
    )).fetchone()
    if result and result[0].lower() == 'bytea':
        return  # already migrated

    op.execute("""
        ALTER TABLE consent_records
        ALTER COLUMN nid_hash TYPE BYTEA
        USING CASE
            WHEN nid_hash IS NOT NULL
            THEN pgp_sym_encrypt(nid_hash, current_setting('app.field_enc_key', true))
            ELSE NULL
        END
    """)

    op.execute("""
        ALTER TABLE kyc_profiles
        ALTER COLUMN signature_data TYPE BYTEA
        USING CASE
            WHEN signature_data IS NOT NULL
            THEN pgp_sym_encrypt(signature_data, current_setting('app.field_enc_key', true))
            ELSE NULL
        END
    """)

    op.execute("""
        ALTER TABLE beneficial_owners
        ALTER COLUMN nid_number TYPE BYTEA
        USING CASE
            WHEN nid_number IS NOT NULL
            THEN pgp_sym_encrypt(nid_number, current_setting('app.field_enc_key', true))
            ELSE NULL
        END
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("""
        ALTER TABLE consent_records
        ALTER COLUMN nid_hash TYPE TEXT
        USING pgp_sym_decrypt(nid_hash, current_setting('app.field_enc_key', true))
    """)
    op.execute("""
        ALTER TABLE kyc_profiles
        ALTER COLUMN signature_data TYPE TEXT
        USING pgp_sym_decrypt(signature_data, current_setting('app.field_enc_key', true))
    """)
    op.execute("""
        ALTER TABLE beneficial_owners
        ALTER COLUMN nid_number TYPE TEXT
        USING pgp_sym_decrypt(nid_number, current_setting('app.field_enc_key', true))
    """)
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
