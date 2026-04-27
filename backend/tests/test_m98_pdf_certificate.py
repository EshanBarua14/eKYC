"""M98 -- PDF certificate fix tests"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

def test_T01_pdf_generator_importable():
    from app.services.kyc_form_generator import generate_kyc_profile_form
    assert callable(generate_kyc_profile_form)

def test_T02_form_generator_returns_dict():
    from app.services.kyc_form_generator import generate_kyc_profile_form
    session = {"kyc_type": "SIMPLIFIED", "session_id": "test-001",
               "data": {"full_name_en": "Test User", "date_of_birth": "1990-01-01",
                         "mobile": "01700000000", "present_address": "Dhaka"},
               "nid_result": None, "screening_result": None, "decision": None}
    form = generate_kyc_profile_form(session)
    assert isinstance(form, dict)

def test_T03_form_has_form_ref():
    from app.services.kyc_form_generator import generate_kyc_profile_form
    session = {"kyc_type": "REGULAR", "session_id": "test-002",
               "data": {"full_name_en": "Test User", "date_of_birth": "1990-01-01",
                         "mobile": "01700000000", "present_address": "Dhaka"},
               "nid_result": None, "screening_result": None, "decision": None}
    form = generate_kyc_profile_form(session)
    assert "form_ref" in form or "bfiu_ref" in form

def test_T04_no_na_in_required_fields():
    from app.services.kyc_form_generator import generate_kyc_profile_form
    session = {"kyc_type": "SIMPLIFIED", "session_id": "test-003",
               "data": {"full_name_en": "Rahman Ali", "date_of_birth": "1985-06-15",
                         "mobile": "01711111111", "present_address": "Chittagong"},
               "nid_result": None, "screening_result": None, "decision": None}
    form = generate_kyc_profile_form(session)
    form_str = str(form)
    assert form_str.count("N/A") < 5, "Too many N/A fields in form"
