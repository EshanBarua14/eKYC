"""
AI Analysis Routes
- POST /api/v1/ai/analyze        — full face analysis
- POST /api/v1/ai/challenge      — single liveness challenge check
- POST /api/v1/ai/scan-nid       — NID card quality check
BFIU Circular No. 29 — Annexure-2
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_analysis import analyze_from_b64, check_liveness_challenge
from app.services.image_utils import b64_to_numpy, detect_face
from app.services.liveness import run_liveness_checks
import cv2
import numpy as np

router = APIRouter(prefix="/ai", tags=["AI Analysis"])

# ── Request Models ────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    image_b64:  str
    session_id: str = "default"

class ChallengeRequest(BaseModel):
    image_b64:  str
    challenge:  str   # center | blink | left | right | smile
    session_id: str = "default"

class NIDScanRequest(BaseModel):
    image_b64:  str
    session_id: str = "default"

# ── Routes ────────────────────────────────────────────────

@router.post(
    "/analyze",
    summary="Full AI face analysis",
    description="""
    Runs complete MediaPipe face analysis on a single image.
    Returns:
    - 468 face landmarks (x,y normalized)
    - Blink detection (eye aspect ratio)
    - Head pose (yaw/pitch in degrees)
    - Head direction (center/left/right/up/down)
    - Smile detection and score
    - Age estimate
    - Skin tone
    """,
)
async def analyze(req: AnalyzeRequest):
    analysis = analyze_from_b64(req.image_b64)
    return {
        "session_id": req.session_id,
        "face_detected":   analysis["face_detected"],
        "landmark_count":  analysis["landmark_count"],
        "landmarks_xy":    analysis["landmarks_xy"],
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


@router.post(
    "/challenge",
    summary="Check single liveness challenge",
    description="""
    Check if a specific liveness challenge is passed in the image.
    **challenge** values:
    - `center` — face looking straight
    - `blink`  — eyes blinking
    - `left`   — head turned left
    - `right`  — head turned right
    - `smile`  — smiling
    """,
)
async def challenge(req: ChallengeRequest):
    valid = ["center", "blink", "left", "right", "smile"]
    if req.challenge not in valid:
        return {"error": f"Invalid challenge. Must be one of: {valid}"}
    result = check_liveness_challenge(req.image_b64, req.challenge)
    return {
        "session_id": req.session_id,
        "challenge":  req.challenge,
        "passed":     result["passed"],
        "reason":     result["reason"],
        "head_direction": result["analysis"].get("head_direction"),
        "blink_detected": result["analysis"].get("blink_detected"),
        "smile_score":    result["analysis"].get("smile_score"),
        "face_detected":  result["analysis"].get("face_detected"),
    }


@router.post(
    "/scan-nid",
    summary="NID card scan quality check",
    description="""
    Analyzes an NID card image for:
    - Card detected (rectangular region)
    - Glare / reflection detected
    - Blur level
    - Brightness adequacy
    - Face detected on card
    - Overall scan quality score
    Per BFIU Circular No. 29 Section 3.3 and Annexure-2d.
    """,
)
async def scan_nid(req: NIDScanRequest):
    img = b64_to_numpy(req.image_b64)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Blur check
    sharpness  = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp_ok   = sharpness > 80

    # Brightness
    brightness = float(gray.mean())
    light_ok   = 40 < brightness < 250

    # Glare detection — look for overexposed regions
    _, thresh   = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    glare_pct   = float(thresh.sum() / 255) / (w * h) * 100
    glare_ok    = glare_pct < 5.0

    # Resolution
    res_ok = w >= 400 and h >= 250

    # Edge detection to find card boundary
    edges      = cv2.Canny(gray, 50, 150)
    contours, _= cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    card_found = False
    card_coords= None
    if contours:
        largest = max(contours, key=cv2.contourArea)
        area    = cv2.contourArea(largest)
        if area > (w * h * 0.1):
            x, y, cw, ch = cv2.boundingRect(largest)
            card_found  = True
            card_coords = {"x": int(x), "y": int(y), "w": int(cw), "h": int(ch)}

    # Face on NID
    face, face_coords = detect_face(img)
    face_found = face is not None

    # Overall score
    checks  = [sharp_ok, light_ok, glare_ok, res_ok, face_found]
    score   = sum(checks)
    quality = ["Poor", "Poor", "Fair", "Good", "Excellent", "Excellent"][score]

    return {
        "session_id":  req.session_id,
        "card_detected": card_found,
        "card_coords":   card_coords,
        "face_on_card":  face_found,
        "face_coords":   face_coords,
        "checks": {
            "sharpness":   {"pass": sharp_ok,  "value": round(sharpness, 1),  "label": "Not Blurry"},
            "lighting":    {"pass": light_ok,  "value": round(brightness, 1), "label": "Adequate Lighting"},
            "glare":       {"pass": glare_ok,  "value": round(glare_pct, 2),  "label": "No Glare (Annexure-2d)"},
            "resolution":  {"pass": res_ok,    "value": f"{w}x{h}",           "label": "Adequate Resolution"},
            "face_found":  {"pass": face_found,"value": str(face_found),      "label": "Face Detected on NID"},
        },
        "quality_score": score,
        "quality_label": quality,
        "bfiu_ref": "BFIU Circular No. 29 — Section 3.3, Annexure-2d",
    }
