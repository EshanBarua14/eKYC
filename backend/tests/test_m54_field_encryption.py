"""M54 — AES-256 Field Encryption Tests — BFIU Circular No. 29 §4.5"""
import pytest
from sqlalchemy import text
from app.db.database import engine


def _conn():
    return engine.connect()


def test_pgcrypto_extension_available():
    with _conn() as conn:
        r = conn.execute(text("SELECT pgp_sym_encrypt('test','key')"))
        assert r.scalar() is not None

def test_nid_hash_column_is_bytea():
    with _conn() as conn:
        r = conn.execute(text("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name='consent_records' AND column_name='nid_hash'
        """))
        assert r.scalar() == "bytea"

def test_signature_data_column_is_bytea():
    with _conn() as conn:
        r = conn.execute(text("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name='kyc_profiles' AND column_name='signature_data'
        """))
        assert r.scalar() == "bytea"

def test_bo_nid_number_column_is_bytea():
    with _conn() as conn:
        r = conn.execute(text("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name='beneficial_owners' AND column_name='nid_number'
        """))
        assert r.scalar() == "bytea"

def test_encrypted_type_importable():
    from app.db.encrypted_type import EncryptedString
    assert EncryptedString is not None

def test_encrypted_type_bind_expression():
    from app.db.encrypted_type import EncryptedString
    import os
    os.environ["EKYC_FIELD_ENCRYPTION_KEY"] = "test_key_32chars_minimum_length!"
    et = EncryptedString()
    assert et.cache_ok is True

def test_roundtrip_encrypt_decrypt():
    with _conn() as conn:
        r = conn.execute(text("""
            SELECT pgp_sym_decrypt(
                pgp_sym_encrypt('BD-NID-9988776655', 'roundtrip_test_key_32chars!!!!!!'),
                'roundtrip_test_key_32chars!!!!!!'
            )
        """))
        assert r.scalar() == "BD-NID-9988776655"

def test_encrypted_value_not_plaintext():
    with _conn() as conn:
        r = conn.execute(text("""
            SELECT pgp_sym_encrypt('SENSITIVE-NID', 'somekey')::text
        """))
        val = r.scalar()
        assert "SENSITIVE-NID" not in val
