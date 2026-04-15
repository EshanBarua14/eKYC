"""
AI Analysis Routes
BFIU Circular No. 29 - Annexure-2
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_analysis import analyze_from_b64, check_liveness_challenge
from app.services.image_utils import b64_to_numpy, detect_face
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
    # Extra check: if face occupies too much of image, it is a selfie not a card
    face_too_large = False
    if face_found and face_coords:
        face_area_pct = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
        face_too_large = face_area_pct > 30
        if face_too_large and "selfie" not in str(nid_issues):
            nid_issues.append(f"Face occupies {face_area_pct:.0f}% of image - this appears to be a selfie or portrait photo. Place your NID card flat and photograph the entire card.")

    is_valid = face_found and size_ok and not face_too_large
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
    # Resize large images to max 1200px to prevent memory issues
    h, w = img.shape[:2]
    if max(h, w) > 1200:
        scale = 1200 / max(h, w)
        img   = cv2.resize(img, (int(w*scale), int(h*scale)))
        h, w  = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Quality checks
    sharpness  = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp_ok   = sharpness > 80
    brightness = float(gray.mean())
    light_ok   = 40 < brightness < 250
    _, thresh  = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    glare_pct  = float(thresh.sum() / 255) / (w * h) * 100
    glare_ok   = glare_pct < 15.0
    res_ok     = w >= 250 and h >= 150

    # Strict NID face detection:
    # 1. Use DNN with high confidence
    # 2. Validate face size ratio - real NID face = 4-35% of card area
    # 3. Too small = false positive, too large = selfie not card
    from app.services.image_utils import _dnn_detect, _haar_detect
    face, face_coords = _dnn_detect(img, conf_threshold=0.55)
    if face is None:
        face, face_coords = _haar_detect(img)
    
    face_found = False
    if face is not None and face_coords:
        face_pct = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
        # Valid NID face: must be 4-35% of image area
        # < 4%  = false positive (pattern/logo detected as face)
        # > 35% = selfie photo, not an ID card
        if 4.0 <= face_pct <= 35.0:
            face_found = True
        else:
            face_coords = None
            face = None

    checks = {
        "sharpness":  {"pass": sharp_ok,   "value": round(sharpness, 1),  "label": "Not Blurry"},
        "lighting":   {"pass": light_ok,   "value": round(brightness, 1), "label": "Adequate Lighting"},
        "glare":      {"pass": glare_ok,   "value": round(glare_pct, 2),  "label": "No Glare (Annexure-2d)"},
        "resolution": {"pass": res_ok,     "value": f"{w}x{h}",           "label": "Adequate Resolution"},
        "face_found": {"pass": face_found, "value": str(face_found),      "label": "Face Detected on NID"},
    }

    score   = sum(v["pass"] for v in checks.values())
    quality = ["Poor","Poor","Fair","Good","Excellent","Excellent"][score]

    # Strict NID validation
    nid_issues = []
    
    # Check 1: Must have a face photo
    if not face_found:
        nid_issues.append("No face photo detected - upload the FRONT side of your NID card")

    # Check 2: Aspect ratio - Bangladesh NID is landscape (ratio ~1.3 to 1.9)
    aspect = w / (h + 1e-6)
    if not (1.1 < aspect < 2.1):
        nid_issues.append(f"Wrong orientation (ratio {aspect:.2f}) - Image is in portrait orientation. Bangladesh NID cards are horizontal - rotate your photo 90 degrees and re-upload.")

    # Check 3: Content density - NID has text, patterns, MRZ lines
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(edges.sum() / 255) / (w * h) * 100
    if edge_density < 1.2:
        nid_issues.append(f"Insufficient card content ({edge_density:.1f}%) - This image does not contain enough card content. Make sure the full NID card is visible and well-lit.")

    # Check 4: Minimum resolution for a card photo
    if w < 300 or h < 180:
        nid_issues.append(f"Image resolution is too low ({w}x{h}px) - take a closer, higher resolution photo")

    # Check 5: Not a portrait photo (person without card)
    # If face takes up more than 40% of image, it is likely a selfie not a card
    if face_found and face_coords:
        face_area_pct = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
        if face_area_pct > 30:
            nid_issues.append(f"Face occupies {face_area_pct:.0f}% of image - this appears to be a selfie or portrait photo. Place your NID card flat and photograph the entire card.")

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
