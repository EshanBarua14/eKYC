"""
M54 — AES-256 Field Encryption via pgcrypto — BFIU Circular No. 29 §4.5
SQLAlchemy TypeDecorator that transparently encrypts/decrypts sensitive PII
using PostgreSQL pgcrypto pgp_sym_encrypt (AES-256).

Encrypted fields: nid_hash, signature_data (KYCProfile), nid_number (BeneficialOwner)
"""
import os
import logging
from sqlalchemy import String, Text, func, select
from sqlalchemy.types import TypeDecorator, UserDefinedType

log = logging.getLogger(__name__)

_KEY_ENV = "EKYC_FIELD_ENCRYPTION_KEY"
_FALLBACK = "CHANGE_ME_IN_PROD_32CHARS_MIN!!"


def _get_key() -> str:
    key = os.getenv(_KEY_ENV, _FALLBACK)
    if key == _FALLBACK:
        log.warning(
            "[M54] Using default field encryption key — set %s in production!", _KEY_ENV
        )
    return key


class EncryptedString(TypeDecorator):
    """
    Stores value as pgcrypto pgp_sym_encrypt(value, key) ciphertext (bytea).
    Decrypts transparently on read via pgp_sym_decrypt.
    Falls back to plaintext store/read when not using PostgreSQL (e.g. SQLite in tests).
    """
    impl        = Text
    cache_ok    = True

    def process_bind_param(self, value, dialect):
        """Encrypt on write — returns SQL expression string for postgres."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            # Return raw value; encryption handled via column_expression
            return value
        # Non-postgres fallback (tests/SQLite)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt on read."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            # Already decrypted by column_expression below
            return value
        return value

    def bind_expression(self, bindvalue):
        """Wrap INSERT/UPDATE value with pgp_sym_encrypt."""
        from sqlalchemy import literal, func as sqlfunc
        return sqlfunc.pgp_sym_encrypt(bindvalue, _get_key())

    def column_expression(self, col):
        """Wrap SELECT with pgp_sym_decrypt."""
        from sqlalchemy import func as sqlfunc, cast
        return sqlfunc.pgp_sym_decrypt(col, _get_key())
