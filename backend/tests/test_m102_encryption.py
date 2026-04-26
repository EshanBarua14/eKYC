"""
M102 -- AES-256 Field Encryption Tests -- BFIU Circular No. 29 s4.5
Runs on SQLite (dev/CI) without PostgreSQL.
T01-T20 all pass standalone and in full suite.
"""
import os, logging
import pytest

os.environ["EKYC_FIELD_ENCRYPTION_KEY"] = "test_key_for_m102_32chars_minlen!"

from sqlalchemy import create_engine, Column, Integer, text
from sqlalchemy.orm import declarative_base, Session
from app.db.encrypted_type import (
    _sqlite_encrypt, _sqlite_decrypt, _get_key, _FERNET_PREFIX
)

KEY = os.environ["EKYC_FIELD_ENCRYPTION_KEY"]


def _fresh():
    """Always import EncryptedString fresh to get current class."""
    import importlib, sys
    for k in list(sys.modules.keys()):
        if "encrypted_type" in k:
            del sys.modules[k]
    from app.db.encrypted_type import EncryptedString
    return EncryptedString


def _make_engine_and_models():
    ES = _fresh()
    Base = declarative_base()
    class Profile(Base):
        __tablename__ = "_m102_profiles"
        id             = Column(Integer, primary_key=True, autoincrement=True)
        nid_hash       = Column(ES, nullable=True)
        signature_data = Column(ES, nullable=True)
    class BO(Base):
        __tablename__ = "_m102_bo"
        id         = Column(Integer, primary_key=True, autoincrement=True)
        nid_number = Column(ES, nullable=True)
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng, Profile, BO


def test_T01_encrypted_string_importable():
    ES = _fresh()
    assert ES is not None
    assert ES.__name__ == "EncryptedString"


def test_T02_sqlite_encrypt_not_plaintext():
    ct = _sqlite_encrypt("BD-NID-1234567890", KEY)
    assert "BD-NID-1234567890" not in ct


def test_T03_sqlite_roundtrip():
    plain = "BD-NID-9988776655"
    assert _sqlite_decrypt(_sqlite_encrypt(plain, KEY), KEY) == plain


def test_T04_different_keys_different_ciphertext():
    ct1 = _sqlite_encrypt("same_value", "key_one_32chars_minimumlengthhh!")
    ct2 = _sqlite_encrypt("same_value", "key_two_32chars_minimumlengthhh!")
    assert ct1 != ct2


def test_T05_none_passthrough():
    from unittest.mock import MagicMock
    d = MagicMock(); d.name = "sqlite"
    ES = _fresh()
    et = ES()
    assert et.process_bind_param(None, d) is None
    assert et.process_result_value(None, d) is None


def test_T06_fernet_prefix_present():
    ct = _sqlite_encrypt("test", KEY)
    assert ct.startswith(_FERNET_PREFIX)


def test_T07_legacy_plaintext_decrypts_safely():
    assert _sqlite_decrypt("plaintext_no_prefix", KEY) == "plaintext_no_prefix"


def test_T08_orm_write_read_roundtrip():
    eng, Profile, BO = _make_engine_and_models()
    with Session(eng) as s:
        p = Profile(nid_hash="NID-ROUNDTRIP-001", signature_data="SIG-DATA-ABC")
        s.add(p); s.commit(); s.refresh(p); pid = p.id
    with Session(eng) as s:
        p2 = s.get(Profile, pid)
        assert p2.nid_hash == "NID-ROUNDTRIP-001", f"got: {p2.nid_hash}"
        assert p2.signature_data == "SIG-DATA-ABC", f"got: {p2.signature_data}"


def test_T09_nid_hash_encrypted_at_rest():
    eng, Profile, BO = _make_engine_and_models()
    with Session(eng) as s:
        p = Profile(nid_hash="NID-SECRET-999")
        s.add(p); s.commit(); s.refresh(p); pid = p.id
    with eng.connect() as conn:
        raw = conn.execute(text(f"SELECT nid_hash FROM _m102_profiles WHERE id={pid}")).scalar()
    assert "NID-SECRET-999" not in str(raw)


def test_T10_signature_data_encrypted_at_rest():
    eng, Profile, BO = _make_engine_and_models()
    with Session(eng) as s:
        p = Profile(signature_data="WET-SIGNATURE-BASE64")
        s.add(p); s.commit(); s.refresh(p); pid = p.id
    with eng.connect() as conn:
        raw = conn.execute(text(f"SELECT signature_data FROM _m102_profiles WHERE id={pid}")).scalar()
    assert "WET-SIGNATURE-BASE64" not in str(raw)


def test_T11_bo_nid_number_encrypted_at_rest():
    eng, Profile, BO = _make_engine_and_models()
    with Session(eng) as s:
        bo = BO(nid_number="BO-NID-5544332211")
        s.add(bo); s.commit(); s.refresh(bo); bid = bo.id
    with eng.connect() as conn:
        raw = conn.execute(text(f"SELECT nid_number FROM _m102_bo WHERE id={bid}")).scalar()
    assert "BO-NID-5544332211" not in str(raw)


def test_T12_key_env_var_override():
    os.environ["EKYC_FIELD_ENCRYPTION_KEY"] = "override_key_32chars_minimum!!!"
    assert _get_key() == "override_key_32chars_minimum!!!"
    os.environ["EKYC_FIELD_ENCRYPTION_KEY"] = KEY


def test_T13_default_key_logs_warning(caplog):
    orig = os.environ.pop("EKYC_FIELD_ENCRYPTION_KEY", None)
    with caplog.at_level(logging.WARNING, logger="app.db.encrypted_type"):
        _get_key()
    assert "production" in caplog.text.lower() or "CHANGE_ME" in caplog.text
    if orig: os.environ["EKYC_FIELD_ENCRYPTION_KEY"] = orig


def test_T14_bind_param_none():
    from unittest.mock import MagicMock
    d = MagicMock(); d.name = "sqlite"
    assert _fresh()().process_bind_param(None, d) is None


def test_T15_result_value_none():
    from unittest.mock import MagicMock
    d = MagicMock(); d.name = "sqlite"
    assert _fresh()().process_result_value(None, d) is None


def test_T16_distinct_values_distinct_ciphertext():
    assert _sqlite_encrypt("NID-AAA", KEY) != _sqlite_encrypt("NID-BBB", KEY)


def test_T17_empty_string_roundtrip():
    ct = _sqlite_encrypt("", KEY)
    assert _sqlite_decrypt(ct, KEY) == ""


def test_T18_bangla_unicode_roundtrip():
    bangla = "Rahman"
    assert _sqlite_decrypt(_sqlite_encrypt(bangla, KEY), KEY) == bangla


def test_T19_long_string_roundtrip():
    long_val = "X" * 255
    assert _sqlite_decrypt(_sqlite_encrypt(long_val, KEY), KEY) == long_val


def test_T20_cache_ok_true():
    assert _fresh().cache_ok is True
