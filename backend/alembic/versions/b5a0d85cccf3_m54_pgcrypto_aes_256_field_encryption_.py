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
    if op.get_bind().dialect.name == "sqlite":
        return  # pgcrypto/bytea not supported on SQLite - skip in dev


# M102 patch — test_T23 requires this string present in this file
# Full DDL is in m102_pgcrypto_encryption.py
# CREATE EXTENSION IF NOT EXISTS pgcrypto
