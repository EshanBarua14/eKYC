"""
Fingerprint test suite — M7
BFIU Circular No. 29 — Section 3.2
Run: python tests/test_fingerprint.py
Requires: uvicorn running on localhost:8000
"""
import json, time
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
time

results = []

def post(ep, payload):
    r = client.post(ep, json=payload)
    r.raise_for_status()
    return r.json()

def get(ep):
    return client.get(ep).json()

def run(name, fn):
    print(f"  Testing: {name}")
    try:
        ok, msg = fn()
        print(f"  {'PASS' if ok else 'FAIL'} — {msg}")
        results.append((name, ok))
    except Exception as e:
        print(f"  FAIL — {e}")
        results.append((name, False))

BASE = {
    "session_id":      f"fp_test_{int(time.time())}",
    "nid_number":      "1234567890123456789",
    "dob":             "01/01/1985",
    "fingerprint_b64": "",
    "finger_position": "RIGHT_INDEX",
}

def test_status_endpoint():
    d = get("/api/v1/fingerprint/status")
    ok = "provider" in d and "bfiu_ref" in d and "hardware_slots" in d
    assert ok, f"provider={d.get('provider')} slots={list(d.get('hardware_slots',{}).keys())}"

def test_demo_match():
    post("/api/v1/fingerprint/demo", {"scenario": "MATCH"})
    d = post("/api/v1/fingerprint/verify", BASE)
    ok = d["verdict"] == "MATCHED" and d["matched"] is True
    assert ok, f"verdict={d['verdict']} score={d['score']} provider={d['provider']}"

def test_demo_no_match():
    post("/api/v1/fingerprint/demo", {"scenario": "NO_MATCH"})
    d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": f"fp_nm_{int(time.time())}"})
    ok = d["verdict"] == "NO_MATCH" and d["matched"] is False
    assert ok, f"verdict={d['verdict']} score={d['score']}"

def test_demo_low_quality():
    post("/api/v1/fingerprint/demo", {"scenario": "LOW_QUALITY"})
    d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": f"fp_lq_{int(time.time())}"})
    ok = d["verdict"] == "LOW_QUALITY"
    assert ok, f"verdict={d['verdict']} quality={d['quality']}"

def test_demo_timeout():
    post("/api/v1/fingerprint/demo", {"scenario": "TIMEOUT"})
    d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": f"fp_to_{int(time.time())}"})
    ok = d["verdict"] == "PROVIDER_TIMEOUT"
    assert ok, f"verdict={d['verdict']}"

def test_response_has_bfiu_fields():
    post("/api/v1/fingerprint/demo", {"scenario": "MATCH"})
    d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": f"fp_bfiu_{int(time.time())}"})
    required = ["verdict","matched","score","attempt_number","attempts_remaining","bfiu_ref","provider","processing_ms"]
    missing  = [k for k in required if k not in d]
    assert len(missing) == 0, f"missing={missing or 'none'}"

def test_attempt_counter_increments():
    post("/api/v1/fingerprint/demo", {"scenario": "NO_MATCH"})
    sess = f"fp_cnt_{int(time.time())}"
    d1 = post("/api/v1/fingerprint/verify", {**BASE, "session_id": sess})
    d2 = post("/api/v1/fingerprint/verify", {**BASE, "session_id": sess})
    ok = d1["attempt_number"] == 1 and d2["attempt_number"] == 2
    assert ok, f"attempt1={d1['attempt_number']} attempt2={d2['attempt_number']}"

def test_attempts_remaining_decrements():
    post("/api/v1/fingerprint/demo", {"scenario": "NO_MATCH"})
    sess = f"fp_rem_{int(time.time())}"
    d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": sess})
    ok = d["attempts_remaining"] == 9
    assert ok, f"remaining={d['attempts_remaining']} (max=10)"

def test_fallback_required_after_3_fails():
    post("/api/v1/fingerprint/demo", {"scenario": "NO_MATCH"})
    sess = f"fp_fb_{int(time.time())}"
    d = None
    for _ in range(3):
        d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": sess})
    ok = d["fallback_required"] is True
    assert ok, f"fallback_required={d['fallback_required']} after 3 attempts"

def test_attempt_limit_enforced():
    post("/api/v1/fingerprint/demo", {"scenario": "NO_MATCH"})
    sess = f"fp_lim_{int(time.time())}"
    d = None
    for _ in range(11):
        d = post("/api/v1/fingerprint/verify", {**BASE, "session_id": sess})
    ok = d["verdict"] == "LIMIT_EXCEEDED"
    assert ok, f"verdict={d['verdict']} after 11 attempts (limit=10)"

def test_invalid_demo_scenario():
    d = post("/api/v1/fingerprint/demo", {"scenario": "INVALID_SCENARIO"})
    ok = "error" in d
    assert ok, f"error={d.get('error','')[:40]}"

def test_hardware_slots_documented():
    d = get("/api/v1/fingerprint/status")
    slots = d.get("hardware_slots", {})
    ok = all(k in slots for k in ["MANTRA","NITGEN","DIGITALPERSONA"])
    assert ok, f"slots={list(slots.keys())}"

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Aegis eKYC — Fingerprint Test Suite (M7)")
    print("  BFIU Circular No. 29 — Section 3.2")
    print("="*55)
    run("Status endpoint returns provider info",   test_status_endpoint)
    run("Demo MATCH returns MATCHED verdict",      test_demo_match)
    run("Demo NO_MATCH returns NO_MATCH verdict",  test_demo_no_match)
    run("Demo LOW_QUALITY returns LOW_QUALITY",    test_demo_low_quality)
    run("Demo TIMEOUT returns PROVIDER_TIMEOUT",   test_demo_timeout)
    run("Response has all BFIU required fields",   test_response_has_bfiu_fields)
    run("Attempt counter increments correctly",    test_attempt_counter_increments)
    run("Attempts remaining decrements from 10",   test_attempts_remaining_decrements)
    run("Fallback required after 3 failed attempts", test_fallback_required_after_3_fails)
    run("Attempt limit enforced at 10 (BFIU §3.2)", test_attempt_limit_enforced)
    run("Invalid demo scenario rejected",          test_invalid_demo_scenario)
    run("All 3 hardware slots documented",         test_hardware_slots_documented)
    print("\n" + "="*55)
    passed = sum(1 for _,ok in results if ok)
    print(f"  Results: {passed}/{len(results)} passed")
    if passed == len(results):
        print("  All tests passed — M7 Fingerprint BFIU compliant")
    else:
        print(f"  Failed: {[n for n,ok in results if not ok]}")
    print("="*55 + "\n")
