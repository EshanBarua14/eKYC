"""M54 pgcrypto AES-256 field encryption nid_hash signature_data bo_nid

Revision ID: b5a0d85cccf3
Revises: 1e6df3c00319
Create Date: 2026-04-23 16:50:41.298981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5a0d85cccf3'
down_revision: Union[str, None] = '1e6df3c00319'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgcrypto extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # KYCProfile / consent_records: nid_hash String->bytea (pgcrypto ciphertext)
    op.execute("""
        ALTER TABLE consent_records
        ALTER COLUMN nid_hash TYPE bytea
        USING pgp_sym_encrypt(COALESCE(nid_hash,''), current_setting('app.encryption_key', true))::bytea
    """)

    # KYCProfile: signature_data Text->bytea
    op.execute("""
        ALTER TABLE kyc_profiles
        ALTER COLUMN signature_data TYPE bytea
        USING CASE WHEN signature_data IS NOT NULL
              THEN pgp_sym_encrypt(signature_data, current_setting('app.encryption_key', true))::bytea
              ELSE NULL END
    """)

    # BeneficialOwner: nid_number String->bytea
    op.execute("""
        ALTER TABLE beneficial_owners
        ALTER COLUMN nid_number TYPE bytea
        USING CASE WHEN nid_number IS NOT NULL
              THEN pgp_sym_encrypt(nid_number, current_setting('app.encryption_key', true))::bytea
              ELSE NULL END
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE consent_records
        ALTER COLUMN nid_hash TYPE varchar(64) USING pgp_sym_decrypt(nid_hash, current_setting('app.encryption_key', true))
    """)
    op.execute("""
        ALTER TABLE kyc_profiles
        ALTER COLUMN signature_data TYPE text USING pgp_sym_decrypt(signature_data, current_setting('app.encryption_key', true))
    """)
    op.execute("""
        ALTER TABLE beneficial_owners
        ALTER COLUMN nid_number TYPE varchar(32) USING pgp_sym_decrypt(nid_number, current_setting('app.encryption_key', true))
    """)
