"""
Image utility functions — DNN-based face detection
Works on NID card photos, low-res, grayscale, document scans.
"""
import base64
import io
import os
import numpy as np
import cv2
from PIL import Image
from fastapi import HTTPException

# ── DNN face detector (much better than Haar for NID photos) ──
_PROTOTXT = os.path.join(os.path.dirname(__file__), "deploy.prototxt")
_MODEL    = os.path.join(os.path.dirname(__file__), "res10_300x300_ssd_iter_140000.caffemodel")
_NET      = None

def _get_net():
    global _NET
    if _NET is None:
        _NET = cv2.dnn.readNetFromCaffe(_PROTOTXT, _MODEL)
    return _NET


def b64_to_numpy(b64: str, max_size: int = 1200) -> np.ndarray:
    """Decode base64 image string to RGB numpy array. Caps at max_size to prevent OOM."""
    try:
        if "," in b64:
            b64 = b64.split(",")[1]
        raw = base64.b64decode(b64)
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = pil.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            pil = pil.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return np.array(pil)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode failed: {str(e)}")


def numpy_to_b64(arr: np.ndarray) -> str:
    """Encode RGB numpy array to base64 JPEG string."""
    pil = Image.fromarray(arr.astype("uint8"))
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def detect_face(img_rgb: np.ndarray, conf_threshold: float = 0.15):
    """
    Detect the largest face using OpenCV DNN (ResNet SSD).
    Falls back to Haar cascade if DNN finds nothing.
    Falls back to center crop if both fail (for NID cards).
    Returns (face_crop_rgb, coords_dict).
    """
    h, w = img_rgb.shape[:2]

    # ── Method 1: DNN detector ────────────────────────────
    face, coords = _dnn_detect(img_rgb, conf_threshold)
    if face is not None:
        return face, coords

    # ── Method 2: Haar cascade fallback ──────────────────
    face, coords = _haar_detect(img_rgb)
    if face is not None:
        return face, coords

    # ── Method 3: Smart center crop (NID document fallback)
    # NID photos: face is usually in upper-center region
    face, coords = _center_crop(img_rgb)
    return face, coords


def _dnn_detect(img_rgb: np.ndarray, conf_threshold: float = 0.15):
    """DNN-based face detection — works on low-quality/document photos."""
    # Hard cap to prevent OOM on large images
    h, w = img_rgb.shape[:2]
    if max(h, w) > 640:
        scale = 640 / max(h, w)
        img_rgb = cv2.resize(img_rgb, (int(w*scale), int(h*scale)))
        h, w = img_rgb.shape[:2]
    net  = _get_net()

    # Preprocess: DNN needs BGR
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    blob    = cv2.dnn.blobFromImage(
        cv2.resize(img_bgr, (300, 300)), 1.0,
        (300, 300), (104.0, 177.0, 123.0)
    )
    net.setInput(blob)
    detections = net.forward()

    best_conf  = 0.0
    best_box   = None

    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence > conf_threshold and confidence > best_conf:
            best_conf = confidence
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            best_box = box.astype(int)

    if best_box is not None:
        x1, y1, x2, y2 = best_box
        margin = int(0.15 * min(x2-x1, y2-y1))
        x1 = max(0, x1 - margin)
        y1 = max(0, y1 - margin)
        x2 = min(w, x2 + margin)
        y2 = min(h, y2 + margin)
        if x2 > x1 and y2 > y1:
            crop   = img_rgb[y1:y2, x1:x2]
            coords = {"x": int(x1), "y": int(y1), "w": int(x2-x1), "h": int(y2-y1)}
            return crop, coords

    return None, None


def _haar_detect(img_rgb: np.ndarray):
    """Haar cascade fallback."""
    h, w = img_rgb.shape[:2]
    # Hard cap — Haar on large images causes OOM
    if max(h, w) > 640:
        scale = 640 / max(h, w)
        img_rgb = cv2.resize(img_rgb, (int(w*scale), int(h*scale)))
        h, w = img_rgb.shape[:2]
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30)
    )
    if len(faces) == 0:
        return None, None

    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    margin = int(0.15 * min(fw, fh))
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(w, x + fw + margin)
    y2 = min(h, y + fh + margin)
    return img_rgb[y1:y2, x1:x2], {"x": int(x1), "y": int(y1), "w": int(x2-x1), "h": int(y2-y1)}


def _center_crop(img_rgb: np.ndarray):
    """
    Smart crop for NID cards where face detection fails.
    NID face is typically in upper-left or upper-center quadrant.
    Returns upper-center 40% of image.
    """
    h, w = img_rgb.shape[:2]
    # Upper center region — where NID photo is typically located
    x1 = int(w * 0.05)
    y1 = int(h * 0.05)
    x2 = int(w * 0.50)
    y2 = int(h * 0.75)
    crop   = img_rgb[y1:y2, x1:x2]
    coords = {"x": x1, "y": y1, "w": x2-x1, "h": y2-y1}
    # Reject blank/uniform images � variance too low to be a real face
    if float(crop.var()) < 50.0:
        return None, None
    return crop, coords
