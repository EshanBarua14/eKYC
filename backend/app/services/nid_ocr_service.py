"""
Xpert Fintech eKYC Platform
NID OCR Service — M35
Extracts Bangla + English fields from NID card images.
Pipeline: decode → preprocess (OpenCV) → OCR (Tesseract) → parse → validate
Falls back to mock data when Tesseract binary not available (dev/CI).
"""
import re
import base64
import hashlib
import logging
import os
from typing import Optional, Tuple
from io import BytesIO
from PIL import Image

log = logging.getLogger(__name__)

# ── Tesseract path config (Windows) ──────────────────────────────────────
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Lenovo\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"E:\Tesseract-OCR\tesseract.exe",
    os.getenv("TESSERACT_CMD", ""),
]

# ── OpenCV availability ───────────────────────────────────────────────────
CV2_AVAILABLE = False
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    pass

# ── Tesseract availability ────────────────────────────────────────────────
TESSERACT_AVAILABLE = False
try:
    import pytesseract

    # Try known Windows paths
    for _path in _TESSERACT_PATHS:
        if _path and os.path.exists(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break

    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
    log.info("[M35] Tesseract available: %s", pytesseract.get_tesseract_version())
except Exception:
    log.warning("[M35] Tesseract not available — using mock OCR fallback")

# ── Image quality thresholds ──────────────────────────────────────────────
MIN_WIDTH    = 300
MIN_HEIGHT   = 200
MIN_DPI      = 72
MAX_FILE_KB  = 10_240   # 10 MB


# ── NID number validation ─────────────────────────────────────────────────
def validate_nid_number(nid: str) -> dict:
    """
    Validate Bangladesh NID number format.
    Old: 13 digits | New: 17 digits | Smart card: 10 digits
    """
    nid = nid.strip().replace(" ", "").replace("-", "")
    if re.match(r"^\d{10}$", nid):
        return {"valid": True,  "format": "smart_card",  "nid": nid}
    if re.match(r"^\d{13}$", nid):
        return {"valid": True,  "format": "old_13digit", "nid": nid}
    if re.match(r"^\d{17}$", nid):
        return {"valid": True,  "format": "new_17digit", "nid": nid}
    return {"valid": False, "format": None, "nid": nid, "reason": "Invalid NID format"}


# ── Image decoding ────────────────────────────────────────────────────────
def decode_base64_image(b64_string: str) -> Optional[Image.Image]:
    """Decode base64 image string to PIL Image."""
    try:
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_string)
        return Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        log.warning("[M35] Image decode error: %s", exc)
        return None


# ── Image quality check ───────────────────────────────────────────────────
def check_image_quality(image: Image.Image) -> dict:
    """
    Check NID image quality before OCR.
    Returns passed, issues list.
    """
    issues = []
    w, h = image.size

    if w < MIN_WIDTH:
        issues.append(f"Image too narrow: {w}px (min {MIN_WIDTH}px)")
    if h < MIN_HEIGHT:
        issues.append(f"Image too short: {h}px (min {MIN_HEIGHT}px)")

    if CV2_AVAILABLE:
        import cv2
        import numpy as np
        arr = np.array(image.convert("L"))
        brightness = float(np.mean(arr))
        sharpness  = float(cv2.Laplacian(arr, cv2.CV_64F).var())

        if brightness < 40:
            issues.append(f"Image too dark: brightness={brightness:.1f}")
        if brightness > 250:
            issues.append(f"Image too bright: brightness={brightness:.1f}")
        if sharpness < 20:
            issues.append(f"Image too blurry: sharpness={sharpness:.1f}")

        return {
            "passed":     len(issues) == 0,
            "issues":     issues,
            "width":      w,
            "height":     h,
            "brightness": round(brightness, 1),
            "sharpness":  round(sharpness, 1),
        }

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "width":  w,
        "height": h,
    }


# ── OpenCV preprocessing ──────────────────────────────────────────────────
def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """
    OpenCV preprocessing pipeline for better OCR accuracy:
    1. Grayscale
    2. Resize to 300 DPI equivalent
    3. Denoise
    4. Adaptive threshold (handles uneven lighting)
    5. Deskew
    """
    if not CV2_AVAILABLE:
        return image

    import cv2
    import numpy as np

    arr = np.array(image)

    # 1. Grayscale
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # 2. Upscale if too small (helps Tesseract accuracy)
    h, w = gray.shape
    if w < 1000:
        scale = 1000 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 4. Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )

    # 5. Deskew
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:
            (h2, w2) = thresh.shape
            center = (w2 // 2, h2 // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(
                thresh, M, (w2, h2),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

    return Image.fromarray(thresh)


# ── OCR field extraction ──────────────────────────────────────────────────
def extract_nid_fields_ocr(image: Image.Image) -> dict:
    """
    Extract NID fields using Tesseract OCR with OpenCV preprocessing.
    Falls back to mock if Tesseract unavailable.
    """
    if not TESSERACT_AVAILABLE:
        return _mock_ocr_result()

    try:
        # Preprocess
        processed = preprocess_for_ocr(image)

        # English extraction
        eng_text = pytesseract.image_to_string(
            processed, config="--psm 6 --oem 3 -l eng"
        )

        # Bengali + English extraction
        ben_text = pytesseract.image_to_string(
            processed, config="--psm 6 --oem 3 -l ben+eng"
        )

        log.debug("[M35] OCR eng_text length: %d", len(eng_text))
        return _parse_nid_text(eng_text, ben_text)

    except Exception as exc:
        log.error("[M35] OCR error: %s", exc)
        return {"error": str(exc), "mode": "ocr_failed"}


# ── Text parser ───────────────────────────────────────────────────────────
def _parse_nid_text(eng_text: str, ben_text: str) -> dict:
    """Parse OCR text to extract structured NID fields."""
    fields = {
        "full_name_en":    None,
        "full_name_bn":    None,
        "date_of_birth":   None,
        "nid_number":      None,
        "fathers_name_en": None,
        "mothers_name_en": None,
        "address":         None,
        "blood_group":     None,
        "mode":            "ocr_live",
    }

    # English name
    name_match = re.search(r"Name[:\s]+([A-Za-z ]+)", eng_text, re.IGNORECASE)
    if name_match:
        fields["full_name_en"] = name_match.group(1).strip()

    # DOB — multiple formats
    dob_match = re.search(
        r"(?:Date of Birth|DOB|Birth)[:\s]*(\d{1,2}[\s/-]\d{1,2}[\s/-]\d{4}|\d{4}-\d{2}-\d{2})",
        eng_text, re.IGNORECASE
    )
    if not dob_match:
        dob_match = re.search(
            r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})",
            eng_text
        )
    if dob_match:
        fields["date_of_birth"] = _normalise_dob(dob_match.group(1).strip())

    # NID number (10, 13, or 17 digits)
    nid_match = re.search(r"\b(\d{17}|\d{13}|\d{10})\b", eng_text)
    if nid_match:
        fields["nid_number"] = nid_match.group(1)

    # Father name
    father_match = re.search(
        r"Father['\u2019s]*[:\s]+([A-Za-z ]+)", eng_text, re.IGNORECASE
    )
    if father_match:
        fields["fathers_name_en"] = father_match.group(1).strip()

    # Mother name
    mother_match = re.search(
        r"Mother['\u2019s]*[:\s]+([A-Za-z ]+)", eng_text, re.IGNORECASE
    )
    if mother_match:
        fields["mothers_name_en"] = mother_match.group(1).strip()

    # Blood group
    blood_match = re.search(r"\b(A|B|AB|O)[+-]", eng_text)
    if blood_match:
        fields["blood_group"] = blood_match.group(0)

    # Address (grab line after "Address:")
    addr_match = re.search(r"Address[:\s]+(.+?)(?:\n|$)", eng_text, re.IGNORECASE)
    if addr_match:
        fields["address"] = addr_match.group(1).strip()

    # Bengali name from ben_text
    bn_match = re.search(r"[\u0980-\u09FF][\u0980-\u09FF\s]+", ben_text)
    if bn_match:
        fields["full_name_bn"] = bn_match.group(0).strip()

    return fields


def _normalise_dob(dob: str) -> str:
    """Normalise DOB to YYYY-MM-DD format."""
    # DD/MM/YYYY → YYYY-MM-DD
    m = re.match(r"(\d{2})[/-](\d{2})[/-](\d{4})", dob)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # Already YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", dob)
    if m:
        return dob
    return dob


# ── Mock OCR fallback ─────────────────────────────────────────────────────
def _mock_ocr_result() -> dict:
    """Return realistic mock NID OCR result for dev/CI."""
    return {
        "full_name_en":    "RAHMAN HOSSAIN CHOWDHURY",
        "full_name_bn":    "রহমান হোসেন চৌধুরী",
        "date_of_birth":   "1994-08-14",
        "nid_number":      "2375411929",
        "fathers_name_en": "ABDUR RAHMAN CHOWDHURY",
        "mothers_name_en": "MST RASHIDA BEGUM",
        "address":         "123 Agrabad, Chittagong",
        "blood_group":     "O+",
        "mode":            "mock",
    }


# ── Main scan function ────────────────────────────────────────────────────
def scan_nid_card(
    front_image_b64: str,
    back_image_b64: Optional[str] = None,
) -> dict:
    """
    Full NID card scan pipeline:
    1. Decode images
    2. Quality check
    3. Preprocess (OpenCV)
    4. OCR (Tesseract / mock fallback)
    5. Parse fields
    6. Validate NID number
    7. Return structured result
    """
    # Decode front image
    front_image = decode_base64_image(front_image_b64)
    if front_image is None:
        return {
            "success":    False,
            "error_code": "IMAGE_DECODE_ERROR",
            "message":    "Could not decode front image",
        }

    # Quality check
    quality = check_image_quality(front_image)
    if not quality["passed"]:
        log.warning("[M35] Image quality issues: %s", quality["issues"])

    # Extract fields from front
    fields = extract_nid_fields_ocr(front_image)

    # Process back image if provided
    back_fields = {}
    if back_image_b64:
        back_image = decode_base64_image(back_image_b64)
        if back_image:
            back_fields = extract_nid_fields_ocr(back_image)

    # Merge (front takes priority)
    merged = {**back_fields, **fields}

    # Validate NID number
    nid_number    = merged.get("nid_number")
    nid_validation = validate_nid_number(nid_number) if nid_number else {
        "valid": False, "reason": "NID number not detected"
    }

    return {
        "success":        True,
        "is_valid_nid":   nid_validation["valid"],
        "nid_format":     nid_validation.get("format"),
        "fields":         merged,
        "quality":        quality,
        "nid_hash":       hashlib.sha256(
                              (nid_number or "").encode()
                          ).hexdigest() if nid_number else None,
        "ocr_mode":       merged.get("mode", "ocr_live"),
        "tesseract_available": TESSERACT_AVAILABLE,
        "cv2_available":       CV2_AVAILABLE,
    }
