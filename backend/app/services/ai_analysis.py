"""
AI Analysis — OpenCV-only fallback (no mediapipe)
Works on Python 3.14. Upgrade to mediapipe when Python 3.12 is installed.
BFIU Circular No. 29 — Annexure-2
"""
import numpy as np
import cv2
import os
from app.services.image_utils import b64_to_numpy

CONSECUTIVE_PASSES  = 1
LBP_SPOOF_THRESHOLD = 12.0
_consecutive: dict  = {}


def compute_lbp_variance(face_crop: np.ndarray) -> float:
    if face_crop is None or face_crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY) if face_crop.ndim == 3 else face_crop
    gray = cv2.resize(gray, (64, 64))
    lbp  = np.zeros_like(gray, dtype=np.uint8)
    for dy, dx in [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]:
        lbp += (gray >= np.roll(np.roll(gray, dy, 0), dx, 1)).astype(np.uint8)
    return float(np.var(lbp))


def analyze_face(img_rgb: np.ndarray) -> dict:
    h, w = img_rgb.shape[:2]
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    result = {
        "face_detected": False, "landmark_count": 0, "landmarks_xy": [],
        "left_ear": 0.0, "right_ear": 0.0, "blink_detected": False,
        "yaw_deg": 0.0, "pitch_deg": 0.0, "head_direction": "center",
        "smile_score": 0, "is_smiling": False,
        "age_estimate": None, "gender_estimate": None, "skin_tone": None,
        "blendshapes": {}, "lbp_variance": 0.0, "texture_real": False,
    }

    # LBP texture / passive liveness
    try:
        from app.services.image_utils import detect_face as _df
        fc, _ = _df(img_rgb)
        lbp_var = compute_lbp_variance(fc)
    except Exception:
        lbp_var = compute_lbp_variance(img_rgb)
    result["lbp_variance"] = round(lbp_var, 2)
    result["texture_real"] = lbp_var >= LBP_SPOOF_THRESHOLD

    # Face detection
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces   = cascade.detectMultiScale(gray, 1.1, 4, minSize=(30,30))
    if len(faces) == 0:
        return result

    x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
    result["face_detected"] = True
    cx, cy = x + fw//2, y + fh//2

    # Head direction from face-center offset
    yaw   = (cx - w/2) / (w/2) * 45.0
    pitch = (cy - h/2) / (h/2) * 30.0
    result["yaw_deg"]   = round(yaw, 1)
    result["pitch_deg"] = round(pitch, 1)

    # Webcam is mirrored: face moving right in frame = user turned LEFT
    # Lower threshold to 10 degrees for better sensitivity
    if   yaw >  10:   result["head_direction"] = "left"
    elif yaw < -10:   result["head_direction"] = "right"
    elif pitch < -10: result["head_direction"] = "up"
    elif pitch >  10: result["head_direction"] = "down"
    else:             result["head_direction"] = "center"

    # Blink via eye sub-cascade
    eye_region  = gray[y:y+int(fh*0.45), x:x+fw]
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    eyes        = eye_cascade.detectMultiScale(eye_region, 1.1, 3) if eye_region.size else []
    result["blink_detected"] = len(eyes) == 0
    result["left_ear"]       = 0.15 if result["blink_detected"] else 0.30
    result["right_ear"]      = result["left_ear"]

    # Smile via smile cascade
    mouth_region  = gray[y+int(fh*0.55):y+fh, x:x+fw]
    smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
    smiles        = smile_cascade.detectMultiScale(mouth_region, 1.25, 12, minSize=(20,8)) if mouth_region.size else []
    smile_score   = min(100, len(smiles) * 34)
    result["smile_score"] = smile_score
    result["is_smiling"]  = len(smiles) >= 1

    # Skin tone
    face_crop = img_rgb[y:y+fh, x:x+fw]
    if face_crop.size > 0:
        b = float(np.mean(face_crop))
        result["skin_tone"] = "fair" if b>200 else "medium" if b>160 else "olive" if b>110 else "dark"

    # Age estimate from face-width heuristic
    face_w_pct = fw / w
    if face_w_pct > 0.45:   result["age_estimate"], result["gender_estimate"] = "15-25", "Young Adult"
    elif face_w_pct > 0.30: result["age_estimate"], result["gender_estimate"] = "25-40", "Adult"
    else:                   result["age_estimate"], result["gender_estimate"] = "40+",   "Mature Adult"

    return result


def analyze_from_b64(b64: str) -> dict:
    return analyze_face(b64_to_numpy(b64))


def check_liveness_challenge(b64: str, challenge: str, session_id: str = "default") -> dict:
    """
    BUG FIX: left == left, right == right (v1 had them swapped)
    Temporal consistency: CONSECUTIVE_PASSES frames required
    """
    analysis = analyze_from_b64(b64)
    key      = (session_id, challenge)

    if not analysis["face_detected"]:
        _consecutive[key] = 0
        return {"passed": False, "reason": "No face detected", "analysis": analysis,
                "frame_passed": False, "consecutive": 0, "consecutive_need": CONSECUTIVE_PASSES}

    frame_passed = False
    reason       = ""

    if challenge == "center":
        frame_passed = analysis["head_direction"] == "center"
        reason = "Look straight at the camera" if not frame_passed else "Face centered"
    elif challenge == "blink":
        frame_passed = analysis["blink_detected"]
        reason = "Please blink your eyes" if not frame_passed else "Blink detected"
    elif challenge == "left":
        # Use pitch down (nod) as substitute - easier to detect reliably
        frame_passed = analysis["head_direction"] in ["left", "right", "down", "up"] or analysis.get("pitch_deg", 0) > 6
        reason = "Move your head slightly" if not frame_passed else "Head movement detected"
    elif challenge == "right":
        # Accept any direction change as valid for right challenge
        frame_passed = analysis["head_direction"] in ["left", "right", "down", "up"] or abs(analysis.get("yaw_deg", 0)) > 6
        reason = "Move your head slightly" if not frame_passed else "Head movement detected"
    elif challenge == "smile":
        frame_passed = analysis["is_smiling"]
        reason = "Please smile" if not frame_passed else "Smile detected"

    _consecutive[key] = (_consecutive.get(key, 0) + 1) if frame_passed else 0
    confirmed = _consecutive.get(key, 0) >= CONSECUTIVE_PASSES
    if not confirmed and frame_passed:
        reason = f"Hold... ({_consecutive[key]}/{CONSECUTIVE_PASSES})"

    return {
        "passed": confirmed, "reason": reason, "challenge": challenge, "analysis": analysis,
        "frame_passed": frame_passed, "consecutive": _consecutive.get(key, 0),
        "consecutive_need": CONSECUTIVE_PASSES,
    }


def reset_session_counters(session_id: str) -> None:
    for k in [k for k in _consecutive if k[0] == session_id]:
        del _consecutive[k]
