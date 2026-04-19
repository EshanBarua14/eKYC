"""
M35 — NID OCR Engine Tests
Tests run in mock mode (Tesseract not required).
"""
import pytest
import base64
from PIL import Image
from io import BytesIO


def _make_test_image_b64(width=400, height=300, color=(200, 200, 200)) -> str:
    """Create a minimal test image as base64."""
    img = Image.new("RGB", (width, height), color=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ══════════════════════════════════════════════════════════════════════════
# 1. NID number validation
# ══════════════════════════════════════════════════════════════════════════
class TestValidateNIDNumber:
    def test_13digit_valid(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("1234567890123")
        assert r["valid"] is True
        assert r["format"] == "old_13digit"

    def test_17digit_valid(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("12345678901234567")
        assert r["valid"] is True
        assert r["format"] == "new_17digit"

    def test_10digit_smart_card(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("1234567890")
        assert r["valid"] is True
        assert r["format"] == "smart_card"

    def test_invalid_length(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("12345")
        assert r["valid"] is False

    def test_strips_spaces(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("  1234567890123  ")
        assert r["valid"] is True

    def test_strips_dashes(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("123-456-789-0123")
        assert r["valid"] is True

    def test_letters_invalid(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("ABCDEFGHIJKLM")
        assert r["valid"] is False

    def test_empty_string_invalid(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("")
        assert r["valid"] is False


# ══════════════════════════════════════════════════════════════════════════
# 2. Image decoding
# ══════════════════════════════════════════════════════════════════════════
class TestDecodeBase64Image:
    def test_valid_image_decodes(self):
        from app.services.nid_ocr_service import decode_base64_image
        b64 = _make_test_image_b64()
        img = decode_base64_image(b64)
        assert img is not None

    def test_invalid_b64_returns_none(self):
        from app.services.nid_ocr_service import decode_base64_image
        result = decode_base64_image("not_valid_base64!!!")
        assert result is None

    def test_data_uri_prefix_stripped(self):
        from app.services.nid_ocr_service import decode_base64_image
        b64 = _make_test_image_b64()
        with_prefix = f"data:image/png;base64,{b64}"
        img = decode_base64_image(with_prefix)
        assert img is not None

    def test_decoded_image_is_rgb(self):
        from app.services.nid_ocr_service import decode_base64_image
        b64 = _make_test_image_b64()
        img = decode_base64_image(b64)
        assert img.mode == "RGB"


# ══════════════════════════════════════════════════════════════════════════
# 3. Image quality check
# ══════════════════════════════════════════════════════════════════════════
class TestCheckImageQuality:
    def test_good_image_passes(self):
        from app.services.nid_ocr_service import check_image_quality
        img = Image.new("RGB", (600, 400), color=(150, 150, 150))
        result = check_image_quality(img)
        assert "passed" in result
        assert "issues" in result

    def test_too_small_image_fails(self):
        from app.services.nid_ocr_service import check_image_quality
        img = Image.new("RGB", (100, 80), color=(150, 150, 150))
        result = check_image_quality(img)
        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_result_has_dimensions(self):
        from app.services.nid_ocr_service import check_image_quality
        img = Image.new("RGB", (600, 400), color=(150, 150, 150))
        result = check_image_quality(img)
        assert result["width"] == 600
        assert result["height"] == 400


# ══════════════════════════════════════════════════════════════════════════
# 4. OCR field extraction (mock mode)
# ══════════════════════════════════════════════════════════════════════════
class TestExtractNIDFieldsOCR:
    def test_returns_dict(self):
        from app.services.nid_ocr_service import extract_nid_fields_ocr
        img = Image.new("RGB", (400, 300), color=(200, 200, 200))
        result = extract_nid_fields_ocr(img)
        assert isinstance(result, dict)

    def test_mock_mode_has_name(self):
        from app.services.nid_ocr_service import extract_nid_fields_ocr, TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            pytest.skip("Tesseract available — mock not used")
        img = Image.new("RGB", (400, 300))
        result = extract_nid_fields_ocr(img)
        assert result["full_name_en"] is not None

    def test_mock_mode_has_dob(self):
        from app.services.nid_ocr_service import extract_nid_fields_ocr, TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            pytest.skip("Tesseract available — mock not used")
        img = Image.new("RGB", (400, 300))
        result = extract_nid_fields_ocr(img)
        assert result["date_of_birth"] == "1990-01-15"

    def test_mock_mode_has_nid_number(self):
        from app.services.nid_ocr_service import extract_nid_fields_ocr, TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            pytest.skip("Tesseract available — mock not used")
        img = Image.new("RGB", (400, 300))
        result = extract_nid_fields_ocr(img)
        assert result["nid_number"] == "1234567890123"

    def test_mock_mode_indicator(self):
        from app.services.nid_ocr_service import extract_nid_fields_ocr, TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            pytest.skip("Tesseract available — mock not used")
        img = Image.new("RGB", (400, 300))
        result = extract_nid_fields_ocr(img)
        assert result["mode"] == "mock"


# ══════════════════════════════════════════════════════════════════════════
# 5. Text parsing
# ══════════════════════════════════════════════════════════════════════════
class TestParseNIDText:
    def test_parses_english_name(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("Name: RAHMAN HOSSAIN\nDOB: 1990-01-15", "")
        assert result["full_name_en"] == "RAHMAN HOSSAIN"

    def test_parses_dob_iso_format(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("Date of Birth: 1990-01-15", "")
        assert result["date_of_birth"] == "1990-01-15"

    def test_parses_dob_slash_format(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("DOB: 15/01/1990", "")
        assert result["date_of_birth"] == "1990-01-15"

    def test_parses_nid_13digit(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("NID: 1234567890123", "")
        assert result["nid_number"] == "1234567890123"

    def test_parses_father_name(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("Father: ABDUR RAHMAN\n", "")
        assert result["fathers_name_en"] == "ABDUR RAHMAN"

    def test_parses_mother_name(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("Mother: RASHIDA BEGUM\n", "")
        assert result["mothers_name_en"] == "RASHIDA BEGUM"

    def test_parses_blood_group(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("Blood Group: O+ ", "")
        assert result["blood_group"] == "O+"

    def test_empty_text_returns_none_fields(self):
        from app.services.nid_ocr_service import _parse_nid_text
        result = _parse_nid_text("", "")
        assert result["full_name_en"] is None
        assert result["nid_number"] is None


# ══════════════════════════════════════════════════════════════════════════
# 6. DOB normalisation
# ══════════════════════════════════════════════════════════════════════════
class TestNormaliseDOB:
    def test_slash_format_normalised(self):
        from app.services.nid_ocr_service import _normalise_dob
        assert _normalise_dob("15/01/1990") == "1990-01-15"

    def test_dash_format_normalised(self):
        from app.services.nid_ocr_service import _normalise_dob
        assert _normalise_dob("15-01-1990") == "1990-01-15"

    def test_iso_format_unchanged(self):
        from app.services.nid_ocr_service import _normalise_dob
        assert _normalise_dob("1990-01-15") == "1990-01-15"


# ══════════════════════════════════════════════════════════════════════════
# 7. scan_nid_card
# ══════════════════════════════════════════════════════════════════════════
class TestScanNIDCard:
    def test_valid_image_returns_success(self):
        from app.services.nid_ocr_service import scan_nid_card
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert result["success"] is True

    def test_invalid_image_returns_error(self):
        from app.services.nid_ocr_service import scan_nid_card
        result = scan_nid_card("invalid_base64!!!")
        assert result["success"] is False
        assert result["error_code"] == "IMAGE_DECODE_ERROR"

    def test_result_has_fields(self):
        from app.services.nid_ocr_service import scan_nid_card
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert "fields" in result

    def test_result_has_quality(self):
        from app.services.nid_ocr_service import scan_nid_card
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert "quality" in result

    def test_result_has_ocr_mode(self):
        from app.services.nid_ocr_service import scan_nid_card
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert "ocr_mode" in result

    def test_mock_mode_nid_is_valid(self):
        from app.services.nid_ocr_service import scan_nid_card, TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            pytest.skip("Tesseract available")
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert result["is_valid_nid"] is True

    def test_mock_mode_nid_hash_present(self):
        from app.services.nid_ocr_service import scan_nid_card, TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE:
            pytest.skip("Tesseract available")
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert result["nid_hash"] is not None
        assert len(result["nid_hash"]) == 64

    def test_with_back_image(self):
        from app.services.nid_ocr_service import scan_nid_card
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64, back_image_b64=b64)
        assert result["success"] is True

    def test_reports_cv2_available(self):
        from app.services.nid_ocr_service import scan_nid_card, CV2_AVAILABLE
        b64 = _make_test_image_b64()
        result = scan_nid_card(b64)
        assert result["cv2_available"] == CV2_AVAILABLE
