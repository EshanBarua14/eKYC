"""
M65/M66/M67 — Bangla OCR + MediaPipe Liveness + Geolocation
BFIU Circular No. 29 compliance tests
"""
import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── M65: Bangla OCR ───────────────────────────────────────────────────────

class TestBanglaOCR:
    def test_tesseract_available(self):
        from app.services.nid_ocr_service import TESSERACT_AVAILABLE
        assert TESSERACT_AVAILABLE, "Tesseract must be available"

    def test_ben_lang_available(self):
        import pytesseract
        langs = pytesseract.get_languages()
        assert "ben" in langs, "Bangla (ben) language pack must be installed"

    def test_eng_lang_available(self):
        import pytesseract
        langs = pytesseract.get_languages()
        assert "eng" in langs

    def test_ocr_ben_eng_config(self):
        """ben+eng config must not raise"""
        import pytesseract
        from PIL import Image
        img = Image.new("RGB", (200, 50), "white")
        try:
            pytesseract.image_to_string(img, config="--psm 6 --oem 3 -l ben+eng")
            assert True
        except Exception as e:
            pytest.fail(f"ben+eng OCR config failed: {e}")

    def test_scan_nid_card_returns_structure(self):
        from app.services.nid_ocr_service import scan_nid_card
        from PIL import Image
        import base64, io
        img = Image.new("RGB", (400, 250), color=(220, 235, 210))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        result = scan_nid_card(b64)
        assert "success" in result
        assert "fields" in result
        assert "ocr_mode" in result
        assert "tesseract_available" in result

    def test_validate_nid_number_10digit(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("1234567890")
        assert r["valid"] is True
        assert r["format"] == "smart_card"

    def test_validate_nid_number_13digit(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("1234567890123")
        assert r["valid"] is True
        assert r["format"] == "old_13digit"

    def test_validate_nid_number_17digit(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("12345678901234567")
        assert r["valid"] is True
        assert r["format"] == "new_17digit"

    def test_validate_nid_invalid(self):
        from app.services.nid_ocr_service import validate_nid_number
        r = validate_nid_number("123")
        assert r["valid"] is False

    def test_mock_ocr_has_bangla_name(self):
        from app.services.nid_ocr_service import _mock_ocr_result
        r = _mock_ocr_result()
        assert r["full_name_bn"] is not None
        assert any("\u0980" <= c <= "\u09FF" for c in r["full_name_bn"])

    def test_preprocess_does_not_crash(self):
        from app.services.nid_ocr_service import preprocess_for_ocr
        from PIL import Image
        img = Image.new("RGB", (400, 250), "white")
        result = preprocess_for_ocr(img)
        assert result is not None


# ── M66: Liveness / MediaPipe ─────────────────────────────────────────────

class TestLivenessService:
    def _make_face_image(self, w=480, h=360):
        """Create a synthetic face-like image."""
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (180, 160, 140)
        # Draw rough face oval
        import cv2
        cx, cy = w//2, h//2
        cv2.ellipse(img, (cx, cy), (80, 100), 0, 0, 360, (220, 190, 160), -1)
        cv2.ellipse(img, (cx-28, cy-20), (16, 10), 0, 0, 360, (60, 40, 30), -1)
        cv2.ellipse(img, (cx+28, cy-20), (16, 10), 0, 0, 360, (60, 40, 30), -1)
        return img

    def test_analyze_face_returns_structure(self):
        from app.services.ai_analysis import analyze_face
        img = self._make_face_image()
        r = analyze_face(img)
        required = ["face_detected","blink_detected","head_direction",
                    "smile_score","is_smiling","yaw_deg","pitch_deg",
                    "lbp_variance","texture_real","engine"]
        for k in required:
            assert k in r, f"Missing key: {k}"

    def test_engine_reported(self):
        from app.services.ai_analysis import analyze_face, MP_AVAILABLE
        img = self._make_face_image()
        r = analyze_face(img)
        assert r["engine"] in ("mediapipe", "opencv")

    def test_compute_lbp_variance_real_face(self):
        from app.services.ai_analysis import compute_lbp_variance
        img = self._make_face_image()
        v = compute_lbp_variance(img)
        assert isinstance(v, float)
        assert v >= 0

    def test_lbp_variance_higher_for_texture(self):
        from app.services.ai_analysis import compute_lbp_variance
        flat = np.full((64,64,3), 128, dtype=np.uint8)
        noise = np.random.randint(0, 255, (64,64,3), dtype=np.uint8)
        assert compute_lbp_variance(noise) > compute_lbp_variance(flat)

    def test_check_liveness_challenge_center(self):
        from app.services.ai_analysis import check_liveness_challenge, reset_session_counters
        import base64, io
        from PIL import Image
        img = Image.new("RGB", (480, 360), (180, 160, 140))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        reset_session_counters("test_center")
        r = check_liveness_challenge(b64, "center", "test_center")
        assert "passed" in r
        assert "reason" in r
        assert "engine" in r["analysis"]
        # anti_spoof only present when face detected
        if r.get("frame_passed"):
            assert "anti_spoof" in r

    def test_check_liveness_invalid_challenge(self):
        from app.services.ai_analysis import check_liveness_challenge
        import base64, io
        from PIL import Image
        img = Image.new("RGB", (480, 360), "white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        r = check_liveness_challenge(b64, "center", "test_invalid")
        assert isinstance(r["passed"], bool)

    def test_reset_session_counters(self):
        from app.services.ai_analysis import _consecutive, reset_session_counters
        _consecutive[("sess_x", "blink")] = 5
        reset_session_counters("sess_x")
        assert ("sess_x", "blink") not in _consecutive

    def test_liveness_checks_bfiu_annexure2(self):
        from app.services.liveness import run_liveness_checks
        img = np.full((360, 480, 3), 128, dtype=np.uint8)
        face = {"x": 160, "y": 80, "w": 160, "h": 200}
        r = run_liveness_checks(img, face)
        required = ["lighting","sharpness","resolution","face_size","overall_pass","score","max_score"]
        for k in required:
            assert k in r
        assert r["max_score"] == 4

    def test_liveness_score_range(self):
        from app.services.liveness import run_liveness_checks
        img = np.full((360, 480, 3), 128, dtype=np.uint8)
        face = {"x": 160, "y": 80, "w": 160, "h": 200}
        r = run_liveness_checks(img, face)
        assert 0 <= r["score"] <= 4


# ── M67: Geolocation middleware ───────────────────────────────────────────

class TestGeolocationMiddleware:
    def test_middleware_file_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "app/middleware/geo_middleware.py"
        assert p.exists()

    def test_is_within_bangladesh_dhaka(self):
        from app.middleware.geo_middleware import is_within_bangladesh
        assert is_within_bangladesh(23.8103, 90.4125) is True  # Dhaka

    def test_is_within_bangladesh_chittagong(self):
        from app.middleware.geo_middleware import is_within_bangladesh
        assert is_within_bangladesh(22.3569, 91.7832) is True  # Chittagong

    def test_is_within_bangladesh_sylhet(self):
        from app.middleware.geo_middleware import is_within_bangladesh
        assert is_within_bangladesh(24.8949, 91.8687) is True  # Sylhet

    def test_outside_bangladesh_india(self):
        from app.middleware.geo_middleware import is_within_bangladesh
        assert is_within_bangladesh(28.6139, 77.2090) is False  # Delhi

    def test_outside_bangladesh_london(self):
        from app.middleware.geo_middleware import is_within_bangladesh
        assert is_within_bangladesh(51.5074, -0.1278) is False  # London

    def test_outside_bangladesh_myanmar(self):
        from app.middleware.geo_middleware import is_within_bangladesh
        assert is_within_bangladesh(16.8661, 96.1951) is False  # Yangon

    def test_bd_bounds_correct(self):
        from app.middleware.geo_middleware import BD_LAT_MIN, BD_LAT_MAX, BD_LON_MIN, BD_LON_MAX
        assert BD_LAT_MIN < 22.0 < BD_LAT_MAX
        assert BD_LON_MIN < 90.0 < BD_LON_MAX

    def test_get_client_ip(self):
        from app.middleware.geo_middleware import get_client_ip
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers.get = lambda k, d="": "1.2.3.4, 5.6.7.8" if k=="X-Forwarded-For" else d
        assert get_client_ip(req) == "1.2.3.4"

    def test_geo_required_prefixes_defined(self):
        from app.middleware.geo_middleware import GEO_REQUIRED_PREFIXES
        assert "/api/v1/ai/" in GEO_REQUIRED_PREFIXES
        assert "/api/v1/face/" in GEO_REQUIRED_PREFIXES
        assert "/api/v1/kyc/" in GEO_REQUIRED_PREFIXES
