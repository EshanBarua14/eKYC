"""
M68 Tests: Nominee validation — BFIU §6.1/§6.2
"""
import pytest
from app.services.nominee_validator import (
    validate_nominee, validate_nominee_from_data,
    NomineeValidationError, ALLOWED_RELATIONS
)


# ── T01-T06: Name validation ──────────────────────────────────────────────
def test_T01_valid_nominee():
    result = validate_nominee("RAHIM UDDIN", "SPOUSE")
    assert result["validated"] == True
    assert result["nominee_name"] == "RAHIM UDDIN"
    assert result["nominee_relation"] == "SPOUSE"

def test_T02_empty_name_fails():
    with pytest.raises(NomineeValidationError) as e:
        validate_nominee("", "SPOUSE")
    assert "nominee_name" in str(e.value)

def test_T03_short_name_fails():
    with pytest.raises(NomineeValidationError):
        validate_nominee("A", "FATHER")

def test_T04_name_with_digits_fails():
    with pytest.raises(NomineeValidationError):
        validate_nominee("Rahim123", "FATHER")

def test_T05_bangla_name_valid():
    result = validate_nominee("রহিম উদ্দিন", "FATHER")
    assert result["validated"] == True

def test_T06_name_normalised_uppercase():
    result = validate_nominee("rahim uddin", "SPOUSE")
    assert result["nominee_name"] == "RAHIM UDDIN"


# ── T07-T10: Relation validation ──────────────────────────────────────────
def test_T07_valid_relation():
    result = validate_nominee("KARIM AHMED", "FATHER")
    assert result["nominee_relation"] == "FATHER"

def test_T08_invalid_relation_fails():
    with pytest.raises(NomineeValidationError) as e:
        validate_nominee("KARIM AHMED", "BOSS")
    assert "nominee_relation" in str(e.value)

def test_T09_empty_relation_fails():
    with pytest.raises(NomineeValidationError):
        validate_nominee("KARIM AHMED", "")

def test_T10_all_allowed_relations_valid():
    for rel in ALLOWED_RELATIONS:
        result = validate_nominee("TEST NAME", rel)
        assert result["validated"] == True


# ── T11-T14: DOB validation ───────────────────────────────────────────────
def test_T11_valid_adult_dob():
    result = validate_nominee("KARIM AHMED", "FATHER", "1970-01-01")
    assert result["nominee_age"] > 18

def test_T12_future_dob_fails():
    with pytest.raises(NomineeValidationError) as e:
        validate_nominee("KARIM AHMED", "FATHER", "2099-01-01")
    assert "future" in str(e.value).lower()

def test_T13_minor_dob_fails_without_flag():
    with pytest.raises(NomineeValidationError) as e:
        validate_nominee("YOUNG KARIM", "SON", "2015-01-01")
    assert "18" in str(e.value)

def test_T14_minor_dob_ok_with_guardian_flag():
    result = validate_nominee("YOUNG KARIM", "SON", "2015-01-01", is_minor_guardian=True)
    assert result["validated"] == True

def test_T14b_invalid_dob_format_fails():
    with pytest.raises(NomineeValidationError):
        validate_nominee("KARIM AHMED", "FATHER", "01/01/1970")


# ── T15-T20: From data dict ───────────────────────────────────────────────
def test_T15_valid_from_data():
    data = {"nominee_name": "RAHIM UDDIN", "nominee_relation": "SPOUSE"}
    result = validate_nominee_from_data(data)
    assert result["validated"] == True

def test_T16_missing_nominee_returns_warning():
    result = validate_nominee_from_data({})
    assert result["validated"] == False
    assert "warning" in result

def test_T17_bfiu_ref_in_result():
    result = validate_nominee("RAHIM UDDIN", "SPOUSE")
    assert "bfiu_ref" in result
    assert "6.1" in result["bfiu_ref"]

def test_T18_partial_nominee_raises():
    with pytest.raises(NomineeValidationError):
        validate_nominee_from_data({"nominee_name": "RAHIM", "nominee_relation": ""})

def test_T19_relation_case_insensitive():
    result = validate_nominee("RAHIM UDDIN", "spouse")
    assert result["nominee_relation"] == "SPOUSE"

def test_T20_allowed_relations_count():
    assert len(ALLOWED_RELATIONS) >= 15
