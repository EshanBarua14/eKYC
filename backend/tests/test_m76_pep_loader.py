"""
M76: PEP data loading script tests — BFIU Circular No. 29 §4.2
"""
import csv
import uuid
import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch
from app.scripts.load_pep_data import (
    BANGLADESH_SEED_PEPS,
    _upsert,
    _update_meta,
    load_seed,
    load_csv,
    load_un_xml,
    VALID_CATEGORIES,
    VALID_RISK,
)
from app.db.models_pep import PEPEntry, PEPListMeta


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_entry(full_name_en="Test Person", category="PEP", status="ACTIVE",
               risk_level="HIGH", ministry_or_org=None, position=None,
               full_name_bn=None):
    e = MagicMock(spec=PEPEntry)
    e.full_name_en = full_name_en
    e.category = category
    e.status = status
    e.risk_level = risk_level
    e.ministry_or_org = ministry_or_org
    e.position = position
    e.full_name_bn = full_name_bn
    e.nationality = "BD"
    e.country = "BD"
    e.notes = None
    e.national_id = None
    e.passport_number = None
    e.date_of_birth = None
    return e


def mock_db_empty():
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.first.return_value = None
    q.filter.return_value.count.return_value = 0
    db.query.return_value = q
    return db


def mock_db_with_entry(entry):
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.first.return_value = entry
    q.filter.return_value.count.return_value = 1
    db.query.return_value = q
    return db


def get_pep_entries_added(db):
    """Filter db.add calls to only PEPEntry instances (exclude PEPListMeta)."""
    return [c[0][0] for c in db.add.call_args_list
            if isinstance(c[0][0], PEPEntry)]


def _write_csv(rows, fieldnames=None):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv",
                                      delete=False, encoding="utf-8")
    if not fieldnames:
        fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    tmp.close()
    return tmp.name


# ── Seed data integrity ───────────────────────────────────────────────────────

def test_seed_has_minimum_entries():
    assert len(BANGLADESH_SEED_PEPS) >= 15

def test_seed_covers_pep_and_ip():
    cats = {r["category"] for r in BANGLADESH_SEED_PEPS}
    assert "PEP" in cats
    assert "IP" in cats

def test_seed_all_valid_categories():
    for row in BANGLADESH_SEED_PEPS:
        assert row["category"] in VALID_CATEGORIES, \
            f"Bad category in: {row['full_name_en']}"

def test_seed_all_valid_risk_levels():
    for row in BANGLADESH_SEED_PEPS:
        assert row.get("risk_level", "HIGH") in VALID_RISK

def test_seed_required_fields_present():
    for row in BANGLADESH_SEED_PEPS:
        assert row.get("full_name_en")
        assert row.get("category")
        assert row.get("position")
        assert row.get("ministry_or_org")

def test_seed_has_bangladesh_bank_governor():
    assert any("Bangladesh Bank" in r.get("ministry_or_org", "")
               for r in BANGLADESH_SEED_PEPS)

def test_seed_has_military_chiefs():
    chiefs = [r for r in BANGLADESH_SEED_PEPS if "Chief of" in r.get("position", "")]
    assert len(chiefs) >= 3

def test_seed_no_duplicate_name_category():
    seen = set()
    for row in BANGLADESH_SEED_PEPS:
        key = (row["full_name_en"], row["category"])
        assert key not in seen, f"Duplicate: {key}"
        seen.add(key)


# ── _upsert ───────────────────────────────────────────────────────────────────

def test_upsert_creates_new_entry():
    db = mock_db_empty()
    data = {"full_name_en": "New Person", "category": "PEP", "risk_level": "HIGH"}
    created, action = _upsert(db, data, "SEED", "ref")
    assert created is True
    assert action == "created"
    db.add.assert_called_once()

def test_upsert_skips_identical():
    existing = make_entry("Same Person", "PEP")
    db = mock_db_with_entry(existing)
    _, action = _upsert(db, {"full_name_en": "Same Person", "category": "PEP"}, "SEED", "ref")
    assert action == "skipped"

def test_upsert_updates_changed_position():
    existing = make_entry("Minister A", "PEP", position="Old")
    db = mock_db_with_entry(existing)
    _, action = _upsert(db, {"full_name_en": "Minister A", "category": "PEP",
                              "position": "New"}, "SEED", "ref")
    assert action == "updated"
    assert existing.position == "New"

def test_upsert_reactivates_inactive():
    existing = make_entry("Old PEP", "PEP", status="INACTIVE")
    db = mock_db_with_entry(existing)
    _, action = _upsert(db, {"full_name_en": "Old PEP", "category": "PEP"}, "SEED", "ref")
    assert action == "updated"
    assert existing.status == "ACTIVE"

def test_upsert_edd_required_true():
    db = mock_db_empty()
    _upsert(db, {"full_name_en": "X", "category": "PEP"}, "SEED", "ref")
    added = db.add.call_args[0][0]
    assert added.edd_required is True

def test_upsert_default_nationality_bd():
    db = mock_db_empty()
    _upsert(db, {"full_name_en": "Y", "category": "IP"}, "SEED", "ref")
    added = db.add.call_args[0][0]
    assert added.nationality == "BD"
    assert added.country == "BD"

def test_upsert_status_active():
    db = mock_db_empty()
    _upsert(db, {"full_name_en": "Z", "category": "PEP"}, "SEED", "ref")
    assert db.add.call_args[0][0].status == "ACTIVE"


# ── load_seed ─────────────────────────────────────────────────────────────────

def test_load_seed_stats():
    db = mock_db_empty()
    stats = load_seed(db)
    assert stats["created"] == len(BANGLADESH_SEED_PEPS)
    assert stats["errors"] == 0 if "errors" in stats else True
    db.commit.assert_called_once()

def test_load_seed_idempotent():
    existing = make_entry()
    db2 = mock_db_with_entry(existing)
    stats = load_seed(db2)
    assert stats["created"] == 0
    assert stats["skipped"] + stats["updated"] == len(BANGLADESH_SEED_PEPS)


# ── load_csv ──────────────────────────────────────────────────────────────────

def test_load_csv_valid_rows():
    rows = [
        {"full_name_en": "CSV One", "category": "PEP", "risk_level": "HIGH"},
        {"full_name_en": "CSV Two", "category": "IP",  "risk_level": "MEDIUM"},
    ]
    path = _write_csv(rows)
    try:
        db = mock_db_empty()
        stats = load_csv(db, path)
        assert stats["created"] == 2
        assert stats["errors"] == 0
        db.commit.assert_called_once()
    finally:
        os.unlink(path)

def test_load_csv_invalid_category_skipped():
    rows = [
        {"full_name_en": "Bad Cat", "category": "UNKNOWN"},
        {"full_name_en": "Good",    "category": "PEP"},
    ]
    path = _write_csv(rows)
    try:
        db = mock_db_empty()
        stats = load_csv(db, path)
        assert stats["errors"] == 1
        assert stats["created"] == 1
    finally:
        os.unlink(path)

def test_load_csv_missing_column_exits(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("position,ministry\nMinister,Dhaka\n")
    with pytest.raises(SystemExit):
        load_csv(mock_db_empty(), str(bad))

def test_load_csv_empty_name_skipped():
    path = _write_csv([{"full_name_en": "", "category": "PEP"}])
    try:
        stats = load_csv(mock_db_empty(), path)
        assert stats["errors"] == 1
        assert stats.get("created", 0) == 0
    finally:
        os.unlink(path)

def test_load_csv_bad_risk_defaults_high():
    rows = [{"full_name_en": "P", "category": "PEP", "risk_level": "RUBBISH"}]
    path = _write_csv(rows)
    try:
        db = mock_db_empty()
        load_csv(db, path)
        entries = get_pep_entries_added(db)
        assert len(entries) == 1
        assert entries[0].risk_level == "HIGH"
    finally:
        os.unlink(path)

def test_load_csv_nationality_truncated():
    rows = [{"full_name_en": "P", "category": "PEP", "nationality": "BGD_EXTRA"}]
    path = _write_csv(rows)
    try:
        db = mock_db_empty()
        load_csv(db, path)
        entries = get_pep_entries_added(db)
        assert len(entries) == 1
        assert len(entries[0].nationality) <= 3
    finally:
        os.unlink(path)

def test_load_csv_file_not_found_exits():
    with pytest.raises(SystemExit):
        load_csv(mock_db_empty(), "/no/such/file.csv")


# ── load_un_xml ───────────────────────────────────────────────────────────────

SAMPLE_UN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<CONSOLIDATED_LIST>
  <INDIVIDUALS>
    <INDIVIDUAL>
      <DATAID>1234</DATAID>
      <REFERENCE_NUMBER>BD-001</REFERENCE_NUMBER>
      <FIRST_NAME>KARIM</FIRST_NAME>
      <SECOND_NAME>UDDIN</SECOND_NAME>
      <NATIONALITY><VALUE>BGD</VALUE></NATIONALITY>
      <INDIVIDUAL_DATE_OF_BIRTH><YEAR>1965</YEAR></INDIVIDUAL_DATE_OF_BIRTH>
      <DESIGNATION><VALUE>Former Minister</VALUE></DESIGNATION>
    </INDIVIDUAL>
    <INDIVIDUAL>
      <DATAID>5678</DATAID>
      <FIRST_NAME>JOHN</FIRST_NAME>
      <NATIONALITY><VALUE>USA</VALUE></NATIONALITY>
    </INDIVIDUAL>
    <INDIVIDUAL>
      <DATAID>9999</DATAID>
    </INDIVIDUAL>
  </INDIVIDUALS>
</CONSOLIDATED_LIST>
"""

def test_un_xml_parses_two_entries(tmp_path):
    f = tmp_path / "un.xml"
    f.write_text(SAMPLE_UN_XML)
    db = mock_db_empty()
    stats = load_un_xml(db, str(f))
    # 2 with names; 1 skipped (no name)
    assert stats["created"] == 2
    assert stats["errors"] == 0

def test_un_xml_sets_pep_category(tmp_path):
    f = tmp_path / "un.xml"
    f.write_text(SAMPLE_UN_XML)
    db = mock_db_empty()
    load_un_xml(db, str(f))
    for e in get_pep_entries_added(db):
        assert e.category == "PEP"

def test_un_xml_sets_high_risk(tmp_path):
    f = tmp_path / "un.xml"
    f.write_text(SAMPLE_UN_XML)
    db = mock_db_empty()
    load_un_xml(db, str(f))
    for e in get_pep_entries_added(db):
        assert e.risk_level == "HIGH"

def test_un_xml_stores_reference(tmp_path):
    f = tmp_path / "un.xml"
    f.write_text(SAMPLE_UN_XML)
    db = mock_db_empty()
    load_un_xml(db, str(f))
    notes = [e.notes for e in get_pep_entries_added(db)]
    assert any("BD-001" in (n or "") for n in notes)

def test_un_xml_commits(tmp_path):
    f = tmp_path / "un.xml"
    f.write_text(SAMPLE_UN_XML)
    db = mock_db_empty()
    load_un_xml(db, str(f))
    db.commit.assert_called_once()

def test_un_xml_file_not_found_exits():
    with pytest.raises(SystemExit):
        load_un_xml(mock_db_empty(), "/no/file.xml")


# ── _update_meta ──────────────────────────────────────────────────────────────

def test_update_meta_creates_record():
    db = mock_db_empty()
    _update_meta(db, "SEED", 22)
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.list_name == "SEED"
    assert added.total_entries == 22
    assert "BFIU Circular No. 29 §4.2" in added.bfiu_ref

def test_update_meta_updates_existing():
    meta = MagicMock(spec=PEPListMeta)
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.first.return_value = meta
    q.filter.return_value.count.return_value = 22
    db.query.return_value = q
    _update_meta(db, "SEED", 22)
    assert meta.total_entries == 22
    db.add.assert_not_called()


# ── Constants ─────────────────────────────────────────────────────────────────

def test_valid_categories():
    assert VALID_CATEGORIES == {"PEP", "IP", "PEP_FAMILY", "PEP_ASSOCIATE"}

def test_valid_risk():
    assert VALID_RISK == {"HIGH", "MEDIUM", "LOW"}
