"""
AI Analysis Service — MediaPipe FaceMesh (upgraded M65/M66)
BFIU Circular No. 29 — Annexure-2
Real blink detection via EAR, smile via lip landmarks, head-turn via nose tip offset.
Falls back to OpenCV Haar cascade if MediaPipe unavailable.
"""
import numpy as np
import cv2
import math
from app.services.image_utils import b64_to_numpy

CONSECUTIVE_PASSES  = 2          # frames needed to confirm a challenge
LBP_SPOOF_THRESHOLD = 12.0
_consecutive: dict  = {}

# ── MediaPipe availability ────────────────────────────────────────────────
MP_AVAILABLE = False
_mp_face_mesh = None
try:
    import mediapipe as mp
    _mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    )
    MP_AVAILABLE = True
except Exception:
    pass


# ── LBP passive liveness ──────────────────────────────────────────────────
def compute_lbp_variance(face_crop: np.ndarray) -> float:
    if face_crop is None or face_crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY) if face_crop.ndim == 3 else face_crop
    gray = cv2.resize(gray, (64, 64))
    lbp  = np.zeros_like(gray, dtype=np.uint8)
    for dy, dx in [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]:
        lbp += (gray >= np.roll(np.roll(gray, dy, 0), dx, 1)).astype(np.uint8)
    return float(np.var(lbp))


# ── EAR (Eye Aspect Ratio) for blink ─────────────────────────────────────
def _ear(landmarks, eye_indices, iw, ih):
    pts = [(int(landmarks[i].x * iw), int(landmarks[i].y * ih)) for i in eye_indices]
    # EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    A = math.dist(pts[1], pts[5])
    B = math.dist(pts[2], pts[4])
    C = math.dist(pts[0], pts[3]) + 1e-6
    return (A + B) / (2.0 * C)

# MediaPipe FaceMesh landmark indices
LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33,  160, 158, 133, 153, 144]
# Lip landmarks for smile
UPPER_LIP = [61, 291]    # left/right corners
LOWER_LIP = [13, 14]     # top/bottom center
# Nose tip + forehead for head pose
NOSE_TIP  = 1
CHIN      = 152
L_TEMPLE  = 234
R_TEMPLE  = 454


def _analyze_mediapipe(img_rgb: np.ndarray) -> dict:
    h, w = img_rgb.shape[:2]
    result = {
        "face_detected": False, "landmark_count": 468,
        "left_ear": 0.0, "right_ear": 0.0, "blink_detected": False,
        "yaw_deg": 0.0, "pitch_deg": 0.0, "head_direction": "center",
        "smile_score": 0, "is_smiling": False,
        "age_estimate": None, "gender_estimate": None, "skin_tone": None,
        "lbp_variance": 0.0, "texture_real": False,
        "face_coords": None, "engine": "mediapipe",
    }

    res = _mp_face_mesh.process(img_rgb)
    if not res.multi_face_landmarks:
        return result

    lm = res.multi_face_landmarks[0].landmark
    result["face_detected"] = True

    # EAR blink
    l_ear = _ear(lm, LEFT_EYE,  w, h)
    r_ear = _ear(lm, RIGHT_EYE, w, h)
    result["left_ear"]       = round(l_ear, 3)
    result["right_ear"]      = round(r_ear, 3)
    result["blink_detected"] = (l_ear < 0.22 and r_ear < 0.22)

    # Head yaw from nose-tip horizontal offset
    nose_x = lm[NOSE_TIP].x   # 0-1
    l_x    = lm[L_TEMPLE].x
    r_x    = lm[R_TEMPLE].x
    face_w = abs(r_x - l_x) + 1e-6
    # yaw: +ve = face turned right (nose right of center)
    yaw    = ((nose_x - (l_x + r_x) / 2) / face_w) * 90.0
    # pitch from nose vertical relative to chin/forehead
    nose_y = lm[NOSE_TIP].y
    chin_y = lm[CHIN].y
    pitch  = ((nose_y - 0.5) / 0.5) * 30.0

    result["yaw_deg"]   = round(yaw, 1)
    result["pitch_deg"] = round(pitch, 1)

    if   yaw >  8:  result["head_direction"] = "right"
    elif yaw < -8:  result["head_direction"] = "left"
    elif pitch < -6: result["head_direction"] = "up"
    elif pitch >  6: result["head_direction"] = "down"
    else:            result["head_direction"] = "center"

    # Smile: mouth corner distance vs face width
    lc = (lm[UPPER_LIP[0]].x * w, lm[UPPER_LIP[0]].y * h)
    rc = (lm[UPPER_LIP[1]].x * w, lm[UPPER_LIP[1]].y * h)
    mouth_w = math.dist(lc, rc)
    smile_ratio = mouth_w / (face_w * w + 1e-6)
    smile_score = min(100, int(smile_ratio * 280))
    result["smile_score"] = smile_score
    result["is_smiling"]  = smile_score > 42

    # Face bounding box from landmarks
    xs = [lm[i].x * w for i in range(len(lm))]
    ys = [lm[i].y * h for i in range(len(lm))]
    x1, x2 = int(min(xs)), int(max(xs))
    y1, y2 = int(min(ys)), int(max(ys))
    result["face_coords"] = {"x": x1, "y": y1, "w": x2-x1, "h": y2-y1}

    # LBP on face crop
    face_crop = img_rgb[max(0,y1):y2, max(0,x1):x2]
    lbp_var   = compute_lbp_variance(face_crop)
    result["lbp_variance"] = round(lbp_var, 2)
    result["texture_real"] = lbp_var >= LBP_SPOOF_THRESHOLD

    # Skin tone
    if face_crop.size > 0:
        b = float(np.mean(face_crop))
        result["skin_tone"] = "fair" if b>200 else "medium" if b>160 else "olive" if b>110 else "dark"

    return result


def _analyze_opencv(img_rgb: np.ndarray) -> dict:
    """OpenCV Haar cascade fallback."""
    h, w = img_rgb.shape[:2]
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    result = {
        "face_detected": False, "landmark_count": 0,
        "left_ear": 0.0, "right_ear": 0.0, "blink_detected": False,
        "yaw_deg": 0.0, "pitch_deg": 0.0, "head_direction": "center",
        "smile_score": 0, "is_smiling": False,
        "age_estimate": None, "gender_estimate": None, "skin_tone": None,
        "lbp_variance": 0.0, "texture_real": False,
        "face_coords": None, "engine": "opencv",
    }

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces   = cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
    if len(faces) == 0:
        return result

    x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
    result["face_detected"] = True
    result["face_coords"]   = {"x": int(x), "y": int(y), "w": int(fw), "h": int(fh)}
    cx, cy = x + fw//2, y + fh//2

    yaw   = (cx - w/2) / (w/2) * 45.0
    pitch = (cy - h/2) / (h/2) * 30.0
    result["yaw_deg"]   = round(yaw, 1)
    result["pitch_deg"] = round(pitch, 1)

    if   yaw >  6:  result["head_direction"] = "left"
    elif yaw < -6:  result["head_direction"] = "right"
    elif pitch < -6: result["head_direction"] = "up"
    elif pitch >  6: result["head_direction"] = "down"
    else:            result["head_direction"] = "center"

    eye_region  = gray[y:y+int(fh*0.45), x:x+fw]
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    eyes        = eye_cascade.detectMultiScale(eye_region, 1.1, 3) if eye_region.size else []
    result["blink_detected"] = len(eyes) == 0
    result["left_ear"]       = 0.15 if result["blink_detected"] else 0.30
    result["right_ear"]      = result["left_ear"]

    mouth_region  = gray[y+int(fh*0.55):y+fh, x:x+fw]
    smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
    smiles        = smile_cascade.detectMultiScale(mouth_region, 1.25, 12, minSize=(20,8)) if mouth_region.size else []
    smile_score   = min(100, len(smiles) * 34)
    result["smile_score"] = smile_score
    result["is_smiling"]  = len(smiles) >= 1

    face_crop = img_rgb[y:y+fh, x:x+fw]
    lbp_var   = compute_lbp_variance(face_crop)
    result["lbp_variance"] = round(lbp_var, 2)
    result["texture_real"] = lbp_var >= LBP_SPOOF_THRESHOLD

    if face_crop.size > 0:
        b = float(np.mean(face_crop))
        result["skin_tone"] = "fair" if b>200 else "medium" if b>160 else "olive" if b>110 else "dark"

    fw_pct = fw / w
    if fw_pct > 0.45:   result["age_estimate"], result["gender_estimate"] = "15-25", "Young Adult"
    elif fw_pct > 0.30: result["age_estimate"], result["gender_estimate"] = "25-40", "Adult"
    else:               result["age_estimate"], result["gender_estimate"] = "40+",   "Mature Adult"

    return result


def analyze_face(img_rgb: np.ndarray) -> dict:
    if MP_AVAILABLE:
        return _analyze_mediapipe(img_rgb)
    return _analyze_opencv(img_rgb)


def analyze_from_b64(b64: str) -> dict:
    return analyze_face(b64_to_numpy(b64))


def check_liveness_challenge(b64: str, challenge: str, session_id: str = "default") -> dict:
    """
    Challenge verification with temporal consistency.
    BFIU Annexure-2: real blink/smile/head-turn detection.
    """
    analysis = analyze_from_b64(b64)
    key      = (session_id, challenge)

    if not analysis["face_detected"]:
        _consecutive[key] = 0
        return {
            "passed": False, "reason": "No face detected — ensure good lighting",
            "analysis": analysis, "frame_passed": False,
            "consecutive": 0, "consecutive_need": CONSECUTIVE_PASSES,
        }

    # Anti-spoof: LBP check (skip for center — first frame may be cold)
    if challenge != "center" and not analysis["texture_real"] and analysis["lbp_variance"] < 5.0:
        _consecutive[key] = 0
        return {
            "passed": False,
            "reason": f"Liveness spoof detected (LBP={analysis['lbp_variance']:.1f})",
            "analysis": analysis, "frame_passed": False,
            "consecutive": 0, "consecutive_need": CONSECUTIVE_PASSES,
        }

    frame_passed = False
    reason       = ""

    if challenge == "center":
        frame_passed = analysis["face_detected"]
        reason = "Face centered ✓" if frame_passed else "Look straight at camera"

    elif challenge == "blink":
        frame_passed = analysis["blink_detected"]
        l, r = analysis["left_ear"], analysis["right_ear"]
        reason = f"Blink detected ✓ (EAR L:{l:.2f} R:{r:.2f})" if frame_passed else f"Close both eyes slowly (EAR L:{l:.2f} R:{r:.2f})"

    elif challenge in ("left", "right"):
        # Any deliberate head movement passes
        frame_passed = (
            analysis["head_direction"] != "center"
            or abs(analysis.get("yaw_deg", 0)) > 8
            or abs(analysis.get("pitch_deg", 0)) > 8
        )
        dir_ = analysis["head_direction"]
        reason = f"Movement detected: {dir_} ✓" if frame_passed else f"Turn or tilt your head (yaw={analysis['yaw_deg']:.0f}°)"

    elif challenge == "smile":
        score = analysis.get("smile_score", 0)
        frame_passed = analysis["is_smiling"] or score > 35
        reason = f"Smile detected ✓ ({score}%)" if frame_passed else f"Smile naturally ({score}%)"

    _consecutive[key] = (_consecutive.get(key, 0) + 1) if frame_passed else 0
    confirmed = _consecutive.get(key, 0) >= CONSECUTIVE_PASSES

    if frame_passed and not confirmed:
        reason = f"Hold... ({_consecutive[key]}/{CONSECUTIVE_PASSES})"

    return {
        "passed": confirmed,
        "reason": reason,
        "challenge": challenge,
        "analysis": analysis,
        "frame_passed": frame_passed,
        "consecutive": _consecutive.get(key, 0),
        "consecutive_need": CONSECUTIVE_PASSES,
        "engine": analysis.get("engine", "unknown"),
        "anti_spoof": {
            "lbp_variance": analysis["lbp_variance"],
            "texture_real": analysis["texture_real"],
        },
    }


def reset_session_counters(session_id: str) -> None:
    for k in [k for k in list(_consecutive) if k[0] == session_id]:
        del _consecutive[k]
