"""
Liveness detection service
BFIU Circular No. 29 — Annexure-2
"""
import numpy as np
import cv2
from app.core.config import settings


def run_liveness_checks(img_rgb: np.ndarray, face_coords: dict) -> dict:
    """
    Run all liveness checks per BFIU Annexure-2.
    Returns structured result dict.
    """
    h, w  = img_rgb.shape[:2]
    gray  = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    # Check 1 — Brightness (Annexure-2b: adequate white lighting)
    brightness   = float(gray.mean())
    lighting_ok  = settings.MIN_BRIGHTNESS < brightness < settings.MAX_BRIGHTNESS

    # Check 2 — Sharpness via Laplacian variance (Annexure-2a: high-resolution)
    sharpness    = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp_ok     = sharpness > settings.MIN_SHARPNESS

    # Check 3 — Minimum resolution (Annexure-2a)
    res_ok       = w >= settings.MIN_WIDTH and h >= settings.MIN_HEIGHT

    # Check 4 — Face size ratio, proxy for depth sensing (Annexure-2g)
    face_ratio   = 0.0
    if face_coords:
        face_ratio = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
    size_ok      = face_ratio > settings.MIN_FACE_AREA_PCT

    passed = sum([lighting_ok, sharp_ok, res_ok, size_ok])

    return {
        "lighting": {
            "pass":  lighting_ok,
            "value": round(brightness, 1),
            "label": "Adequate Lighting (Annexure-2b)",
        },
        "sharpness": {
            "pass":  sharp_ok,
            "value": round(sharpness, 1),
            "label": "Image Sharpness (Annexure-2a)",
        },
        "resolution": {
            "pass":  res_ok,
            "value": f"{w}x{h}",
            "label": "Minimum Resolution (Annexure-2a)",
        },
        "face_size": {
            "pass":  size_ok,
            "value": round(face_ratio, 1),
            "label": "Face Size / Depth Proxy (Annexure-2g)",
        },
        "overall_pass": passed >= 3,
        "score":        passed,
        "max_score":    4,
    }
