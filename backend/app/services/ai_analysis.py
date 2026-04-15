"""
AI Analysis Service — MediaPipe Tasks API (v0.10.x)
- Face landmark detection (478 points)
- Blink detection (eye aspect ratio)
- Head pose estimation (yaw/pitch)
- Smile detection
- Age & skin tone estimation
BFIU Circular No. 29 — Annexure-2
"""
import numpy as np
import cv2
import math
import os
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from app.services.image_utils import b64_to_numpy

# ── Model path ────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
MODEL_PATH = os.path.abspath(MODEL_PATH)

# ── Landmark indices (MediaPipe 478-point model) ──────────
# Eye EAR indices
LEFT_EAR_IDX  = [362, 385, 387, 263, 373, 380]
RIGHT_EAR_IDX = [33,  160, 158, 133, 153, 144]

# Head pose
NOSE_TIP    = 1
CHIN        = 152
LEFT_EAR_P  = 234
RIGHT_EAR_P = 454
LEFT_EYE_C  = 33
RIGHT_EYE_C = 263

# Smile
MOUTH_LEFT  = 61
MOUTH_RIGHT = 291
TOP_LIP     = 0
BOT_LIP     = 17

def _get_landmarker():
    """Create a FaceLandmarker instance."""
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=mp_vision.RunningMode.IMAGE,
    )
    return mp_vision.FaceLandmarker.create_from_options(options)

def eye_aspect_ratio(landmarks, eye_indices, img_w, img_h):
    """Calculate Eye Aspect Ratio for blink detection."""
    pts = [(landmarks[i].x * img_w, landmarks[i].y * img_h) for i in eye_indices]
    v1  = math.dist(pts[1], pts[5])
    v2  = math.dist(pts[2], pts[4])
    h   = math.dist(pts[0], pts[3])
    return (v1 + v2) / (2.0 * h + 1e-6)

def get_head_pose(landmarks):
    """Estimate yaw and pitch from face landmarks."""
    nose    = landmarks[NOSE_TIP]
    l_ear   = landmarks[LEFT_EAR_P]
    r_ear   = landmarks[RIGHT_EAR_P]
    l_eye   = landmarks[LEFT_EYE_C]
    r_eye   = landmarks[RIGHT_EYE_C]
    chin    = landmarks[CHIN]

    ear_dist   = abs(r_ear.x - l_ear.x)
    nose_x_rel = (nose.x - l_ear.x) / (ear_dist + 1e-6)
    yaw_deg    = (nose_x_rel - 0.5) * 2 * 45

    eye_mid_y  = (l_eye.y + r_eye.y) / 2
    pitch_raw  = (nose.y - eye_mid_y) / (abs(chin.y - eye_mid_y) + 1e-6)
    pitch_deg  = (pitch_raw - 0.5) * 60

    return round(yaw_deg, 1), round(pitch_deg, 1)

def get_smile_score(landmarks):
    """Estimate smile intensity from mouth geometry."""
    lc = landmarks[MOUTH_LEFT]
    rc = landmarks[MOUTH_RIGHT]
    tl = landmarks[TOP_LIP]
    bl = landmarks[BOT_LIP]

    mouth_w     = abs(rc.x - lc.x)
    mouth_h     = abs(bl.y - tl.y)
    avg_corner_y= (lc.y + rc.y) / 2
    center_y    = (tl.y + bl.y) / 2
    corner_lift = center_y - avg_corner_y
    smile_ratio = mouth_h / (mouth_w + 1e-6)
    score       = min(100, max(0, int((corner_lift * 300) + (smile_ratio * 100))))
    return score

def get_blendshape_value(blendshapes, name):
    """Extract a blendshape score by name."""
    if not blendshapes:
        return 0.0
    for b in blendshapes:
        if b.category_name == name:
            return round(b.score, 3)
    return 0.0

def analyze_face(img_rgb: np.ndarray) -> dict:
    """Full MediaPipe face analysis. Returns all signals."""
    h, w = img_rgb.shape[:2]

    result = {
        "face_detected":   False,
        "landmark_count":  0,
        "landmarks_xy":    [],
        "left_ear":        0.0,
        "right_ear":       0.0,
        "blink_detected":  False,
        "yaw_deg":         0.0,
        "pitch_deg":       0.0,
        "head_direction":  "center",
        "smile_score":     0,
        "is_smiling":      False,
        "age_estimate":    None,
        "gender_estimate": None,
        "skin_tone":       None,
        "blendshapes":     {},
    }

    try:
        landmarker = _get_landmarker()
        mp_image   = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        detection  = landmarker.detect(mp_image)
        landmarker.close()
    except Exception as e:
        result["error"] = str(e)
        return result

    if not detection.face_landmarks:
        return result

    lms = detection.face_landmarks[0]
    result["face_detected"]  = True
    result["landmark_count"] = len(lms)

    # Landmarks for frontend overlay (every 4th for performance)
    result["landmarks_xy"] = [
        {"x": round(lm.x, 4), "y": round(lm.y, 4)}
        for i, lm in enumerate(lms) if i % 4 == 0
    ]

    # Blendshapes (if available)
    if detection.face_blendshapes:
        bs = detection.face_blendshapes[0]
        result["blendshapes"] = {
            "blink_left":  get_blendshape_value(bs, "eyeBlinkLeft"),
            "blink_right": get_blendshape_value(bs, "eyeBlinkRight"),
            "smile_left":  get_blendshape_value(bs, "mouthSmileLeft"),
            "smile_right": get_blendshape_value(bs, "mouthSmileRight"),
            "jaw_open":    get_blendshape_value(bs, "jawOpen"),
        }
        # Use blendshapes for blink if available
        blink_l = result["blendshapes"]["blink_left"]
        blink_r = result["blendshapes"]["blink_right"]
        if blink_l > 0 or blink_r > 0:
            result["blink_detected"] = (blink_l > 0.4 and blink_r > 0.4)
            result["left_ear"]       = round(1.0 - blink_l, 3)
            result["right_ear"]      = round(1.0 - blink_r, 3)

        # Use blendshapes for smile if available
        smile_l = result["blendshapes"]["smile_left"]
        smile_r = result["blendshapes"]["smile_right"]
        if smile_l > 0 or smile_r > 0:
            smile_avg = (smile_l + smile_r) / 2
            result["smile_score"] = int(smile_avg * 100)
            result["is_smiling"]  = smile_avg > 0.35

    # Fallback to geometry if blendshapes not available
    if not result["blendshapes"]:
        left_ear  = eye_aspect_ratio(lms, LEFT_EAR_IDX,  w, h)
        right_ear = eye_aspect_ratio(lms, RIGHT_EAR_IDX, w, h)
        result["left_ear"]      = round(left_ear, 3)
        result["right_ear"]     = round(right_ear, 3)
        result["blink_detected"]= (left_ear < 0.2 and right_ear < 0.2)
        smile = get_smile_score(lms)
        result["smile_score"]   = smile
        result["is_smiling"]    = smile > 30

    # Head pose
    yaw, pitch = get_head_pose(lms)
    result["yaw_deg"]   = yaw
    result["pitch_deg"] = pitch

    if yaw < -15:
        result["head_direction"] = "left"
    elif yaw > 15:
        result["head_direction"] = "right"
    elif pitch < -15:
        result["head_direction"] = "up"
    elif pitch > 15:
        result["head_direction"] = "down"
    else:
        result["head_direction"] = "center"

    # Skin tone from nose region
    cx = int(lms[NOSE_TIP].x * w)
    cy = int(lms[NOSE_TIP].y * h)
    r  = max(10, int(0.05 * min(w, h)))
    patch = img_rgb[max(0,cy-r):min(h,cy+r), max(0,cx-r):min(w,cx+r)]
    if patch.size > 0:
        brightness = float(np.mean(patch))
        result["skin_tone"] = (
            "fair"   if brightness > 200 else
            "medium" if brightness > 160 else
            "olive"  if brightness > 110 else
            "dark"
        )

    # Age estimate from eye-face width ratio
    l_eye = lms[LEFT_EYE_C]
    r_eye = lms[RIGHT_EYE_C]
    l_ear_lm = lms[LEFT_EAR_P]
    r_ear_lm = lms[RIGHT_EAR_P]
    eye_dist = abs(r_eye.x - l_eye.x)
    face_w   = abs(r_ear_lm.x - l_ear_lm.x)
    ratio    = eye_dist / (face_w + 1e-6)

    if ratio > 0.42:
        result["age_estimate"]    = "15–25"
        result["gender_estimate"] = "Young Adult"
    elif ratio > 0.36:
        result["age_estimate"]    = "25–40"
        result["gender_estimate"] = "Adult"
    else:
        result["age_estimate"]    = "40+"
        result["gender_estimate"] = "Mature Adult"

    return result


def analyze_from_b64(b64: str) -> dict:
    img = b64_to_numpy(b64)
    return analyze_face(img)


def check_liveness_challenge(b64: str, challenge: str) -> dict:
    """Check if a specific liveness challenge is passed."""
    analysis = analyze_from_b64(b64)

    if not analysis["face_detected"]:
        return {"passed": False, "reason": "No face detected", "analysis": analysis}

    passed = False
    reason = ""

    if challenge == "center":
        passed = analysis["head_direction"] == "center"
        reason = "Look straight at the camera" if not passed else "✓ Face centered"
    elif challenge == "blink":
        passed = analysis["blink_detected"]
        reason = "Please blink your eyes" if not passed else "✓ Blink detected"
    elif challenge == "left":
        passed = analysis["head_direction"] == "left"
        reason = "Turn your head to the LEFT" if not passed else "✓ Left turn detected"
    elif challenge == "right":
        passed = analysis["head_direction"] == "right"
        reason = "Turn your head to the RIGHT" if not passed else "✓ Right turn detected"
    elif challenge == "smile":
        passed = analysis["is_smiling"]
        reason = "Please smile" if not passed else "✓ Smile detected"

    return {"passed": passed, "reason": reason, "challenge": challenge, "analysis": analysis}
