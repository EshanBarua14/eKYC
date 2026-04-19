"""
AI Analysis Routes — v2
BFIU Circular No. 29 — Annexure-2
Changes: /challenge passes session_id, returns consecutive progress + lbp_variance
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_analysis import (
    analyze_from_b64, check_liveness_challenge, reset_session_counters,
)
from app.services.image_utils import b64_to_numpy, _dnn_detect, _haar_detect
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


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    a = analyze_from_b64(req.image_b64)
    return {
        "session_id": req.session_id,
        "face_detected": a["face_detected"], "landmark_count": a["landmark_count"],
        "landmarks_xy": a["landmarks_xy"],
        "blink":      {"detected": a["blink_detected"], "left_ear": a["left_ear"], "right_ear": a["right_ear"]},
        "head_pose":  {"yaw_deg": a["yaw_deg"], "pitch_deg": a["pitch_deg"], "direction": a["head_direction"]},
        "expression": {"smile_score": a["smile_score"], "is_smiling": a["is_smiling"]},
        "attributes": {"age_estimate": a["age_estimate"], "gender_estimate": a["gender_estimate"], "skin_tone": a["skin_tone"]},
        "passive_liveness": {"lbp_variance": a["lbp_variance"], "texture_real": a["texture_real"]},
    }


@router.post("/challenge")
async def challenge(req: ChallengeRequest):
    valid = ["center", "blink", "left", "right", "smile"]
    if req.challenge not in valid:
        return {"error": f"Invalid challenge. Must be one of: {valid}"}
    result = check_liveness_challenge(req.image_b64, req.challenge, req.session_id)
    a = result["analysis"]
    return {
        "session_id": req.session_id, "challenge": req.challenge,
        "passed": result["passed"], "reason": result["reason"],
        "head_direction": a.get("head_direction"), "blink_detected": a.get("blink_detected"),
        "smile_score": a.get("smile_score"),       "face_detected": a.get("face_detected"),
        "consecutive": result.get("consecutive", 0), "consecutive_need": result.get("consecutive_need", 1),
        "lbp_variance": a.get("lbp_variance", 0.0), "texture_real": a.get("texture_real", True),
    }


@router.post("/reset-session")
async def reset_session(req: AnalyzeRequest):
    reset_session_counters(req.session_id)
    return {"session_id": req.session_id, "reset": True}


@router.post("/scan-nid")
async def scan_nid(req: NIDScanRequest):
    img  = b64_to_numpy(req.image_b64)
    h, w = img.shape[:2]
    if max(h, w) > 1200:
        scale = 1200 / max(h, w)
        img   = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        h, w  = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    hsv  = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    sharpness  = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    _, thr     = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    glare_pct  = float(thr.sum() / 255) / (w * h) * 100

    face, face_coords = _dnn_detect(img, conf_threshold=0.3)
    if face is None:
        face, face_coords = _haar_detect(img)
    face_found = False
    if face is not None and face_coords:
        fp = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
        if 2.0 <= fp <= 50.0:
            face_found = True
        else:
            face = face_coords = None

    checks = {
        "sharpness":  {"pass": sharpness > 80,          "value": round(sharpness,1),  "label": "Not Blurry"},
        "lighting":   {"pass": 40 < brightness < 250,   "value": round(brightness,1), "label": "Adequate Lighting"},
        "glare":      {"pass": glare_pct < 15.0,        "value": round(glare_pct,2),  "label": "No Glare (Annexure-2d)"},
        "resolution": {"pass": w >= 250 and h >= 150,   "value": f"{w}x{h}",          "label": "Adequate Resolution"},
        "face_found": {"pass": face_found,               "value": str(face_found),     "label": "Face on NID"},
    }
    score   = sum(v["pass"] for v in checks.values())
    quality = ["Poor","Poor","Fair","Good","Excellent","Excellent"][score]

    nid_green      = cv2.inRange(hsv, np.array([35,20,50]),   np.array([95,255,255]))
    nid_red        = cv2.inRange(hsv, np.array([0,100,100]),  np.array([10,255,255]))
    green_pct      = float(nid_green.sum()/255)/(w*h)*100
    red_pct        = float(nid_red.sum()/255)/(w*h)*100
    has_nid_colors = green_pct >= 3.0 and red_pct >= 0.05

    nid_issues = []
    if not has_nid_colors:
        nid_issues.append(f"Missing Bangladesh NID green ({green_pct:.1f}%). Upload FRONT of NID card.")
    if w / (h + 1e-6) < 1.0:
        nid_issues.append("Wrong orientation — NID is landscape. Rotate 90°.")
    if w < 250 or h < 150:
        nid_issues.append(f"Image too small ({w}x{h}px).")
    edges     = cv2.Canny(gray, 50, 150)
    edge_dens = float(edges.sum()/255)/(w*h)*100
    if edge_dens < 2.5 and has_nid_colors:
        nid_issues.append(f"Insufficient text content ({edge_dens:.1f}%).")

    is_nid = len(nid_issues) == 0
    if not is_nid:
        quality = "Invalid"; score = min(score, 1)

    # Extract OCR fields from front image
    try:
        from app.services.nid_ocr_service import scan_nid_card
        ocr = scan_nid_card(front_image_b64=req.image_b64)
        fields = ocr.get("fields", {})
    except Exception:
        fields = {}
    return {
        "session_id": req.session_id, "is_valid_nid": is_nid,
        "nid_issues": nid_issues,     "face_on_card": face_found,
        "face_coords": face_coords,   "checks": checks,
        "quality_score": score,       "quality_label": quality,
        "fields":        fields,
        "bfiu_ref": "BFIU Circular No. 29 - Section 3.3, Annexure-2d",
    }
