from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import cv2
import base64
import io
import time
from PIL import Image

app = FastAPI(title="Xpert Fintech eKYC - Face Verification API v1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def b64_to_numpy(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",")[1]
    raw = base64.b64decode(b64)
    pil = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(pil)

def detect_face(img_rgb: np.ndarray):
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
    )
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    margin = int(0.2 * min(w, h))
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(img_rgb.shape[1], x + w + margin)
    y2 = min(img_rgb.shape[0], y + h + margin)
    face_crop = img_rgb[y1:y2, x1:x2]
    return face_crop, {"x": int(x1), "y": int(y1), "w": int(x2-x1), "h": int(y2-y1)}

def liveness_checks(img_rgb: np.ndarray, face_coords) -> dict:
    h, w = img_rgb.shape[:2]
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    brightness = float(gray.mean())
    lighting_ok = 40 < brightness < 250

    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp_ok = sharpness > 80

    res_ok = w >= 320 and h >= 240

    face_ratio = 0.0
    if face_coords:
        face_ratio = (face_coords["w"] * face_coords["h"]) / (w * h) * 100
    size_ok = face_ratio > 4.0

    passed = sum([lighting_ok, sharp_ok, res_ok, size_ok])

    return {
        "lighting":    {"pass": lighting_ok, "value": round(brightness, 1), "label": "Adequate Lighting (Annexure-2b)"},
        "sharpness":   {"pass": sharp_ok,    "value": round(sharpness, 1),  "label": "Image Sharpness (Annexure-2a)"},
        "resolution":  {"pass": res_ok,      "value": f"{w}x{h}",           "label": "Minimum Resolution (Annexure-2a)"},
        "face_size":   {"pass": size_ok,     "value": round(face_ratio, 1), "label": "Face Size / Depth Proxy (Annexure-2g)"},
        "overall_pass": passed >= 3,
        "score": passed,
        "max_score": 4,
    }

def compare_faces(face1_rgb: np.ndarray, face2_rgb: np.ndarray) -> dict:
    size = (128, 128)
    f1 = cv2.resize(face1_rgb, size)
    f2 = cv2.resize(face2_rgb, size)

    hist_scores = []
    for ch in range(3):
        h1 = cv2.calcHist([f1], [ch], None, [64], [0, 256])
        h2 = cv2.calcHist([f2], [ch], None, [64], [0, 256])
        cv2.normalize(h1, h1)
        cv2.normalize(h2, h2)
        hist_scores.append(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL))
    hist_score = float(np.mean(hist_scores))

    g1 = cv2.cvtColor(f1, cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(f2, cv2.COLOR_RGB2GRAY)
    orb = cv2.ORB_create(nfeatures=300)
    kp1, des1 = orb.detectAndCompute(g1, None)
    kp2, des2 = orb.detectAndCompute(g2, None)
    orb_score = 0.0
    if des1 is not None and des2 is not None and len(des1) > 5 and len(des2) > 5:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        good = [m for m in matches if m.distance < 60]
        orb_score = min(1.0, len(good) / max(len(kp1), len(kp2), 1) * 3)

    diff = cv2.absdiff(g1, g2).astype(float)
    pixel_score = 1.0 - (diff.mean() / 255.0)

    final = (hist_score * 0.35) + (orb_score * 0.40) + (pixel_score * 0.25)
    final = round(max(0.0, min(1.0, final)) * 100, 2)

    return {
        "histogram_score": round(hist_score * 100, 2),
        "feature_score":   round(orb_score * 100, 2),
        "pixel_score":     round(pixel_score * 100, 2),
        "confidence":      final,
    }

def face_to_b64(face_rgb: np.ndarray) -> str:
    pil = Image.fromarray(face_rgb)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

# ─────────────────────────────────────────
# Models
# ─────────────────────────────────────────

class VerifyRequest(BaseModel):
    nid_image_b64: str
    live_image_b64: str
    session_id: str = "demo"

# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "Xpert Fintech eKYC API", "version": "1.0"}

@app.post("/api/verify")
async def verify(req: VerifyRequest):
    start = time.time()

    try:
        nid_img  = b64_to_numpy(req.nid_image_b64)
        live_img = b64_to_numpy(req.live_image_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode error: {str(e)}")

    nid_face,  nid_coords  = detect_face(nid_img)
    live_face, live_coords = detect_face(live_img)

    nid_face_found  = nid_face is not None
    live_face_found = live_face is not None

    liveness = liveness_checks(live_img, live_coords)

    match_result = None
    if nid_face_found and live_face_found:
        match_result = compare_faces(nid_face, live_face)

    confidence = match_result["confidence"] if match_result else 0

    if not nid_face_found:
        verdict = "FAILED"
        verdict_reason = "No face detected in NID image"
    elif not live_face_found:
        verdict = "FAILED"
        verdict_reason = "No face detected in live capture"
    elif not liveness["overall_pass"]:
        verdict = "FAILED"
        verdict_reason = "Liveness checks failed — retake photo per BFIU Annexure-2"
    elif confidence >= 55:
        verdict = "MATCHED"
        verdict_reason = "Face biometric verified successfully"
    elif confidence >= 38:
        verdict = "REVIEW"
        verdict_reason = "Low confidence — manual review recommended"
    else:
        verdict = "FAILED"
        verdict_reason = "Face biometric mismatch"

    elapsed = round((time.time() - start) * 1000, 1)

    return {
        "session_id":     req.session_id,
        "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "processing_ms":  elapsed,
        "verdict":        verdict,
        "verdict_reason": verdict_reason,
        "confidence":     confidence,
        "faces": {
            "nid_face_detected":  nid_face_found,
            "live_face_detected": live_face_found,
            "nid_face_coords":    nid_coords,
            "live_face_coords":   live_coords,
            "nid_face_preview":   face_to_b64(nid_face)  if nid_face_found  else None,
            "live_face_preview":  face_to_b64(live_face) if live_face_found else None,
        },
        "liveness": liveness,
        "match_scores": match_result,
        "bfiu_ref": {
            "guideline": "BFIU Circular No. 29",
            "section":   "3.3 — Customer Onboarding by Face-Matching",
            "annexure":  "Annexure-2 — Instructions for Photo Capture",
        }
    }
