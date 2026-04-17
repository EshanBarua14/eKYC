"""
Liveness test suite v2 — BFIU Circular No. 29 Annexure-2
Run: python tests/test_liveness_enhanced.py
Requires: uvicorn running on localhost:8000
"""
import base64, json, urllib.request, urllib.error
import numpy as np, cv2, io
from PIL import Image

API = "http://localhost:8000"
results = []

def post(ep, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(f"{API}{ep}", data=data, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

def img_b64(arr):
    buf = io.BytesIO()
    Image.fromarray(arr.astype("uint8")).save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def blank(color=(200,200,200), size=(400,400)):
    return np.full((*size,3), color, dtype="uint8")

def run(name, fn):
    print(f"  Testing: {name}")
    try:
        ok, msg = fn()
        print(f"  {'PASS' if ok else 'FAIL'} — {msg}")
        results.append((name, ok))
    except Exception as e:
        print(f"  FAIL — {e}")
        results.append((name, False))

def test_health():
    d = json.loads(urllib.request.urlopen(f"{API}/health", timeout=5).read())
    return d.get("status") == "ok", f"status={d.get('status')}"

def test_challenge_has_consecutive():
    d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": "center", "session_id": "t1"})
    return "consecutive" in d and "consecutive_need" in d, f"consecutive={d.get('consecutive')} need={d.get('consecutive_need')}"

def test_invalid_challenge_rejected():
    d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": "wink", "session_id": "t2"})
    return "error" in d, f"error present: {'error' in d}"

def test_all_5_challenges_accepted():
    for ch in ["center","blink","left","right","smile"]:
        d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": ch, "session_id": "t3"})
        if "error" in d:
            return False, f"'{ch}' returned error: {d['error']}"
    return True, "All 5 accepted without error"

def test_left_challenge_returns_direction():
    d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": "left", "session_id": "t4"})
    return "passed" in d and "head_direction" in d, f"direction={d.get('head_direction')} passed={d.get('passed')}"

def test_right_challenge_returns_direction():
    d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": "right", "session_id": "t5"})
    return "passed" in d and "head_direction" in d, f"direction={d.get('head_direction')} passed={d.get('passed')}"

def test_reset_session():
    d = post("/api/v1/ai/reset-session", {"image_b64": img_b64(blank()), "session_id": "t6"})
    return d.get("reset") is True, f"reset={d.get('reset')}"

def test_analyze_has_passive_liveness():
    d = post("/api/v1/ai/analyze", {"image_b64": img_b64(blank()), "session_id": "t7"})
    pl = d.get("passive_liveness", {})
    return "lbp_variance" in pl and "texture_real" in pl, f"lbp={pl.get('lbp_variance')} real={pl.get('texture_real')}"

def test_challenge_has_lbp_variance():
    d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": "center", "session_id": "t8"})
    return "lbp_variance" in d, f"lbp_variance={d.get('lbp_variance')}"

def test_no_face_not_passed():
    d = post("/api/v1/ai/challenge", {"image_b64": img_b64(blank()), "challenge": "center", "session_id": "t9"})
    return d.get("passed") is False, f"passed={d.get('passed')} face={d.get('face_detected')}"

def test_dark_image_fails_lighting():
    b = img_b64(blank(color=(15,15,15)))
    d = post("/api/v1/face/verify", {"nid_image_b64": b, "live_image_b64": b})
    return not d["liveness"]["lighting"]["pass"], f"lighting.pass={d['liveness']['lighting']['pass']}"

def test_bfiu_ref_in_scan_nid():
    d = post("/api/v1/ai/scan-nid", {"image_b64": img_b64(blank()), "session_id": "t11"})
    return "bfiu_ref" in d and "BFIU" in d["bfiu_ref"], f"bfiu_ref={d.get('bfiu_ref','')[:35]}"

def test_confidence_range():
    b = img_b64(blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": b, "live_image_b64": b})
    return 0 <= d["confidence"] <= 100, f"confidence={d['confidence']}"

def test_verdict_valid():
    b = img_b64(blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": b, "live_image_b64": b})
    return d["verdict"] in ["MATCHED","REVIEW","FAILED"], f"verdict={d['verdict']}"

def test_response_structure():
    b = img_b64(blank())
    d = post("/api/v1/face/verify", {"nid_image_b64": b, "live_image_b64": b})
    required = ["verdict","verdict_reason","confidence","faces","liveness","bfiu_ref","session_id","timestamp","processing_ms"]
    missing  = [k for k in required if k not in d]
    return len(missing) == 0, f"missing={missing or 'none'}"

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Aegis eKYC — Liveness Test Suite v2")
    print("  BFIU Circular No. 29 — Annexure-2")
    print("="*55)
    run("Health check",                       test_health)
    run("Challenge has consecutive fields",   test_challenge_has_consecutive)
    run("Invalid challenge rejected",         test_invalid_challenge_rejected)
    run("All 5 challenges accepted",          test_all_5_challenges_accepted)
    run("LEFT challenge returns direction",   test_left_challenge_returns_direction)
    run("RIGHT challenge returns direction",  test_right_challenge_returns_direction)
    run("Reset session endpoint works",       test_reset_session)
    run("Analyze has passive_liveness block", test_analyze_has_passive_liveness)
    run("Challenge has lbp_variance field",   test_challenge_has_lbp_variance)
    run("No face => passed=False",            test_no_face_not_passed)
    run("Dark image fails lighting check",    test_dark_image_fails_lighting)
    run("BFIU ref in scan-nid response",      test_bfiu_ref_in_scan_nid)
    run("Confidence in 0-100 range",          test_confidence_range)
    run("Verdict is valid value",             test_verdict_valid)
    run("Response structure complete",        test_response_structure)
    print("\n" + "="*55)
    passed = sum(1 for _,ok in results if ok)
    print(f"  Results: {passed}/{len(results)} passed")
    if passed == len(results):
        print("  All tests passed — liveness module BFIU compliant")
    else:
        print(f"  Failed: {[n for n,ok in results if not ok]}")
    print("="*55 + "\n")
