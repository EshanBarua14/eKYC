"""
AI Analysis Routes
BFIU Circular No. 29 - Annexure-2
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_analysis import analyze_from_b64, check_liveness_challenge
from app.services.image_utils import b64_to_numpy, detect_face, _dnn_detect, _haar_detect
from app.services.liveness import run_liveness_checks
import cv2
import numpy as np

router = APIRouter(prefix="/ai", tags=["AI Analysis"])

class AnalyzeRequest(BaseModel):
    image_b64:  str
    session_id: str = "default"

class ChallengeRequest(BaseModel):
    image_b64:  str
    challenge:  str
    session_id: str = "default"

class NIDScanRequest(BaseModel):
    image_b64:  str
    session_id: str = "default"


def validate_nid_card(img: np.ndarray, checks: dict) -> tuple:
    """Check if image is a valid Bangladesh NID card."""
    h, w   = img.shape[:2]
    gray   = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Aspect ratio check - NID is 85.6x54mm = ~1.58 ratio, allow some tolerance
    aspect    = w / (h + 1e-6)
    aspect_ok = 0.4 < aspect < 3.5

    # Edge density - NID has lots of text and patterns
    edges        = cv2.Canny(gray, 50, 150)
    edge_density = float(edges.sum() / 255) / (w * h) * 100
    text_ok      = edge_density > 0.8

    # Minimum size
    size_ok = w >= 200 and h >= 100

    # Face detected on card
    face_ok = checks.get("face_found", {}).get("pass", False)

    reasons = []
    if not aspect_ok: reasons.append(f"Wrong aspect ratio ({aspect:.2f}) - NID cards are landscape rectangular")
    if not text_ok:   reasons.append(f"Insufficient card content (edge density {edge_density:.1f}%) - upload front of NID card")
    if not size_ok:   reasons.append(f"Image resolution is too low ({w}-{h}px) - take a closer, sharper photo of your NID card")

    # Valid NID = face detected + reasonable size
    # Face detection is the PRIMARY check - if face found on card, it is likely an ID
    # Aspect ratio is secondary - only reject if clearly wrong AND no face
    # Strict NID validation checks
    face_ok = checks.get('face_found', {}).get('pass', False)
    face_coords_val = checks.get('face_coords')
    reasons = []

    face_too_large = False
    face_too_dark  = False
    low_content    = False

    if not face_ok:
        reasons.append('No face photo detected - upload the FRONT side of your Bangladesh NID card showing your photo.')

    if face_ok and face_coords_val:
        face_area_pct = (face_coords_val['w'] * face_coords_val['h']) / (w * h) * 100

        if face_area_pct > 30:
            face_too_large = True
            reasons.append(f'Face occupies {face_area_pct:.0f}% of image - upload the NID card, not a selfie or portrait photo.')

        if edge_density < 1.8 and face_area_pct > 12:
            low_content = True
            reasons.append(f'Insufficient card content ({edge_density:.1f}%) - this does not appear to be a Bangladesh NID card.')

        face_crop = img[face_coords_val['y']:face_coords_val['y']+face_coords_val['h'],
                        face_coords_val['x']:face_coords_val['x']+face_coords_val['w']]
        if face_crop.size > 0:
            face_mean = float(cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY).mean())
            if face_mean < 60:
                face_too_dark = True
                reasons.append(f'Face region brightness ({face_mean:.0f}) is too low - this appears to be a graphic or logo, not a real NID photograph.')

    is_valid = face_ok and size_ok and not face_too_large and not face_too_dark and not low_content
    return is_valid, reasons


@router.post("/analyze", summary="Full AI face analysis")
async def analyze(req: AnalyzeRequest):
    analysis = analyze_from_b64(req.image_b64)
    return {
        "session_id":    req.session_id,
        "face_detected": analysis["face_detected"],
        "landmark_count":analysis["landmark_count"],
        "landmarks_xy":  analysis["landmarks_xy"],
        "blink": {
            "detected":  analysis["blink_detected"],
            "left_ear":  analysis["left_ear"],
            "right_ear": analysis["right_ear"],
        },
        "head_pose": {
            "yaw_deg":   analysis["yaw_deg"],
            "pitch_deg": analysis["pitch_deg"],
            "direction": analysis["head_direction"],
        },
        "expression": {
            "smile_score": analysis["smile_score"],
            "is_smiling":  analysis["is_smiling"],
        },
        "attributes": {
            "age_estimate":    analysis["age_estimate"],
            "gender_estimate": analysis["gender_estimate"],
            "skin_tone":       analysis["skin_tone"],
        },
    }


@router.post("/challenge", summary="Check single liveness challenge")
async def challenge(req: ChallengeRequest):
    valid = ["center", "blink", "left", "right", "smile"]
    if req.challenge not in valid:
        return {"error": f"Invalid challenge. Must be one of: {valid}"}
    result = check_liveness_challenge(req.image_b64, req.challenge)
    return {
        "session_id":     req.session_id,
        "challenge":      req.challenge,
        "passed":         result["passed"],
        "reason":         result["reason"],
        "head_direction": result["analysis"].get("head_direction"),
        "blink_detected": result["analysis"].get("blink_detected"),
        "smile_score":    result["analysis"].get("smile_score"),
        "face_detected":  result["analysis"].get("face_detected"),
    }


@router.post("/scan-nid", summary="NID card scan quality check")
async def scan_nid(req: NIDScanRequest):
    img  = b64_to_numpy(req.image_b64)
    h, w = img.shape[:2]
    if max(h, w) > 1200:
        scale = 1200 / max(h, w)
        img   = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        h, w  = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    hsv  = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    # ── Quality checks ──────────────────────────────────────
    sharpness  = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp_ok   = sharpness > 80
    brightness = float(gray.mean())
    light_ok   = 40 < brightness < 250
    _, thr     = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    glare_pct  = float(thr.sum() / 255) / (w * h) * 100
    glare_ok   = glare_pct < 15.0
    res_ok     = w >= 250 and h >= 150

    # ── Face detection ──────────────────────────────────────
    face, face_coords = _dnn_detect(img, conf_threshold=0.3)
    if face is None:
        face, face_coords = _haar_detect(img)

    face_found = False
    if face is not None and face_coords:
        fp = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
        if 2.0 <= fp <= 50.0:
            face_found = True
        else:
            face = None
            face_coords = None

    checks = {
        "sharpness":  {"pass": sharp_ok,   "value": round(sharpness, 1),  "label": "Not Blurry"},
        "lighting":   {"pass": light_ok,   "value": round(brightness, 1), "label": "Adequate Lighting"},
        "glare":      {"pass": glare_ok,   "value": round(glare_pct, 2),  "label": "No Glare (Annexure-2d)"},
        "resolution": {"pass": res_ok,     "value": f"{w}x{h}",           "label": "Adequate Resolution"},
        "face_found": {"pass": face_found, "value": str(face_found),      "label": "Face Detected on NID"},
    }

    score   = sum(v["pass"] for v in checks.values())
    quality = ["Poor","Poor","Fair","Good","Excellent","Excellent"][score]

    # ── Bangladesh NID color signature (PRIMARY validator) ──
    # Bangladesh NID cards have a distinctive green/teal background
    # HSV range tuned for the specific green of Bangladesh NIDs
    nid_green  = cv2.inRange(hsv, np.array([35, 20, 50]),  np.array([95, 255, 255]))
    green_pct  = float(nid_green.sum() / 255) / (w * h) * 100

    # Also check for the red Bangladesh emblem present on all NIDs
    nid_red    = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    red_pct    = float(nid_red.sum() / 255) / (w * h) * 100

    # A Bangladesh NID must have significant green AND some red (emblem)
    has_nid_colors = green_pct >= 3.0 and red_pct >= 0.05

    # ── NID Validation ──────────────────────────────────────
    nid_issues = []

    # Rule 1: Must pass NID color signature
    if not has_nid_colors:
        if green_pct < 3.0:
            nid_issues.append(f"Image does not have the green color of a Bangladesh NID card (green: {green_pct:.1f}%). Upload the FRONT side of your green Bangladesh NID card.")
        if red_pct < 0.05:
            nid_issues.append(f"Bangladesh NID emblem (red seal) not detected (red: {red_pct:.2f}%). Make sure the full card front is visible.")

    # Rule 2: Orientation check
    aspect = w / (h + 1e-6)
    if aspect < 1.0:
        nid_issues.append(f"Wrong orientation ({aspect:.2f}) - Bangladesh NID cards are horizontal. Rotate 90 degrees and re-upload.")

    # Rule 3: Minimum size
    if not res_ok:
        nid_issues.append(f"Image too small ({w}x{h}px). Take a closer, higher resolution photo of your NID card.")

    # Rule 4: Text/content density - NID cards have dense Bangla text, borders, MRZ
    edges      = cv2.Canny(gray, 50, 150)
    edge_dens  = float(edges.sum() / 255) / (w * h) * 100
    if edge_dens < 2.5 and has_nid_colors:
        nid_issues.append(f"Insufficient text content ({edge_dens:.1f}%) - Bangladesh NID cards have dense text. Make sure the full card is visible and in focus.")

    is_nid = len(nid_issues) == 0
    if not is_nid:
        quality = "Invalid"
        score   = min(score, 1)

    return {
        "session_id":    req.session_id,
        "is_valid_nid":  is_nid,
        "nid_issues":    nid_issues,
        "face_on_card":  face_found,
        "face_coords":   face_coords,
        "checks":        checks,
        "quality_score": score,
        "quality_label": quality,
        "bfiu_ref":      "BFIU Circular No. 29 - Section 3.3, Annexure-2d",
    }
