"""
Xpert Fintech eKYC — Backend Test Suite
BFIU Circular No. 29 — Section 3.3 Face Matching
"""
import base64
import json
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
import numpy as np
import cv2
import io
from PIL import Image, ImageDraw


PASS  = "✅ PASS"
FAIL  = "❌ FAIL"
results = []

def post(endpoint, payload):
    r = client.post(endpoint, json=payload)
    r.raise_for_status()
    return r.json()

def img_to_b64(arr: np.ndarray) -> str:
    pil = Image.fromarray(arr.astype("uint8"))
    buf = io.BytesIO()
    pil.save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def make_blank(color=(200,200,200), size=(300,300)):
    return np.full((*size, 3), color, dtype="uint8")

def make_face_image(bg=(220,220,220), skin=(210,180,140), size=(400,400)):
    """Draw a synthetic oval face so OpenCV Haar cascade can detect it."""
    img = np.full((*size, 3), bg, dtype="uint8")
    h, w = size
    # Face oval
    cx, cy = w//2, h//2
    cv2.ellipse(img, (cx, cy), (90, 115), 0, 0, 360, skin, -1)
    # Eyes
    cv2.ellipse(img, (cx-35, cy-25), (18, 12), 0, 0, 360, (255,255,255), -1)
    cv2.ellipse(img, (cx+35, cy-25), (18, 12), 0, 0, 360, (255,255,255), -1)
    cv2.circle(img, (cx-35, cy-25), 8, (40, 30, 20), -1)
    cv2.circle(img, (cx+35, cy-25), 8, (40, 30, 20), -1)
    cv2.circle(img, (cx-35, cy-25), 3, (0, 0, 0), -1)
    cv2.circle(img, (cx+35, cy-25), 3, (0, 0, 0), -1)
    # Nose
    pts = np.array([[cx, cy+5],[cx-12, cy+35],[cx+12, cy+35]], np.int32)
    cv2.polylines(img, [pts], True, (180,140,110), 2)
    # Mouth
    cv2.ellipse(img, (cx, cy+60), (30, 15), 0, 0, 180, (160,80,80), 2)
    # Eyebrows
    cv2.line(img, (cx-52, cy-42), (cx-18, cy-38), (80,55,35), 4)
    cv2.line(img, (cx+18, cy-38), (cx+52, cy-42), (80,55,35), 4)
    return img

def run(name, fn):
    print(f"\n  Testing: {name}")
    try:
        ok, msg = fn()
        status = PASS if ok else FAIL
        print(f"  {status} — {msg}")
        results.append((name, ok, msg))
    except Exception as e:
        print(f"  {FAIL} — Exception: {e}")
        results.append((name, False, str(e)))

# ── Tests ────────────────────────────────────────────────

def test_health():
    d = client.get("/health").json()
    assert d.get("status") in ("ok","healthy"), f"health={d}"

def test_no_face_both():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    ok = d["verdict"] == "FAILED"
    assert ok, f"verdict={d['verdict']}  reason='{d['verdict_reason']}'"

def test_missing_fields():
    r = client.post("/api/v1/face/verify", json={})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

def test_dark_image_liveness():
    dark = make_blank(color=(15, 15, 15))
    b64  = img_to_b64(dark)
    d    = post("/api/v1/face/verify", {"nid_image_b64": b64, "live_image_b64": b64})
    lighting_pass = d["liveness"]["lighting"]["pass"]
    ok = not lighting_pass
    assert ok, f"lighting.pass={lighting_pass}  brightness={d['liveness']['lighting']['value']}"

def test_bright_image_liveness():
    bright = make_blank(color=(245, 245, 245))
    b64    = img_to_b64(bright)
    d      = post("/api/v1/face/verify", {"nid_image_b64": b64, "live_image_b64": b64})
    lighting_pass = d["liveness"]["lighting"]["pass"]
    ok = lighting_pass
    assert ok, f"lighting.pass={lighting_pass}  brightness={d['liveness']['lighting']['value']}"

def test_low_resolution_liveness():
    tiny = make_blank(size=(100, 80))
    b64  = img_to_b64(tiny)
    d    = post("/api/v1/face/verify", {"nid_image_b64": b64, "live_image_b64": b64})
    res_pass = d["liveness"]["resolution"]["pass"]
    ok = not res_pass
    assert ok, f"resolution.pass={res_pass}  value={d['liveness']['resolution']['value']}"

def test_adequate_resolution_liveness():
    big = make_blank(size=(480, 640))
    b64 = img_to_b64(big)
    d   = post("/api/v1/face/verify", {"nid_image_b64": b64, "live_image_b64": b64})
    res_pass = d["liveness"]["resolution"]["pass"]
    ok = res_pass
    assert ok, f"resolution.pass={res_pass}  value={d['liveness']['resolution']['value']}"

def test_session_id_returned():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {
        "nid_image_b64": blank,
        "live_image_b64": blank,
        "session_id": "unit_test_999"
    })
    ok = d["session_id"] == "unit_test_999"
    assert ok, f"session_id='{d['session_id']}'"

def test_bfiu_ref_present():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    ok = "bfiu_ref" in d and d["bfiu_ref"]["guideline"] == "BFIU Circular No. 29"
    assert ok, f"guideline='{d.get('bfiu_ref',{}).get('guideline')}'"

def test_processing_time_present():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    ok = "processing_ms" in d and d["processing_ms"] > 0
    assert ok, f"processing_ms={d.get('processing_ms')}"

def test_response_structure():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    required = ["verdict","verdict_reason","confidence","faces","liveness","bfiu_ref","session_id","timestamp","processing_ms"]
    missing  = [k for k in required if k not in d]
    ok = len(missing) == 0
    assert ok, f"missing fields: {missing if missing else 'none — all present'}"

def test_verdict_values_valid():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    ok = d["verdict"] in ["MATCHED", "REVIEW", "FAILED"]
    assert ok, f"verdict='{d['verdict']}' is a valid value"

def test_confidence_range():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    c  = d["confidence"]
    ok = 0 <= c <= 100
    assert ok, f"confidence={c}  in range [0, 100]"

def test_liveness_structure():
    blank = img_to_b64(make_blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": blank, "live_image_b64": blank})
    lv = d["liveness"]
    required = ["lighting","sharpness","resolution","face_size","overall_pass","score","max_score"]
    missing  = [k for k in required if k not in lv]
    ok = len(missing) == 0
    assert ok, f"missing liveness keys: {missing if missing else 'none — all present'}"

def test_blurry_image_sharpness():
    img  = make_blank(size=(400,400))
    blur = cv2.GaussianBlur(img, (51,51), 0)
    b64  = img_to_b64(blur)
    d    = post("/api/v1/face/verify", {"nid_image_b64": b64, "live_image_b64": b64})
    sharp_pass = d["liveness"]["sharpness"]["pass"]
    ok = not sharp_pass
    assert ok, f"sharpness.pass={sharp_pass}  score={d['liveness']['sharpness']['value']}"

# ── Runner ───────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═"*55)
    print("  Xpert Fintech eKYC — Test Suite")
    print("  BFIU Circular No. 29 — Section 3.3")
    print("═"*55)

    run("Health check",                    test_health)
    run("No face in both images → FAILED", test_no_face_both)
    run("Missing fields → 422 error",      test_missing_fields)
    run("Dark image fails lighting check", test_dark_image_liveness)
    run("Bright image passes lighting",    test_bright_image_liveness)
    run("Low resolution fails check",      test_low_resolution_liveness)
    run("Adequate resolution passes",      test_adequate_resolution_liveness)
    run("Session ID returned correctly",   test_session_id_returned)
    run("BFIU reference present",          test_bfiu_ref_present)
    run("Processing time present",         test_processing_time_present)
    run("Response structure complete",     test_response_structure)
    run("Verdict is valid value",          test_verdict_values_valid)
    run("Confidence in range 0–100",       test_confidence_range)
    run("Liveness structure complete",     test_liveness_structure)
    run("Blurry image fails sharpness",    test_blurry_image_sharpness)

    print("\n" + "═"*55)
    passed = sum(1 for _, ok, _ in results if ok)
    total  = len(results)
    pct    = round(passed/total*100)
    print(f"  Results: {passed}/{total} passed ({pct}%)")
    if passed == total:
        print("  ✅ All tests passed — API is BFIU compliant")
    else:
        failed = [n for n, ok, _ in results if not ok]
        print(f"  ❌ Failed: {', '.join(failed)}")
    print("═"*55 + "\n")
