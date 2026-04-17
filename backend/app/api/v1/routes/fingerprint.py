"""
Fingerprint Verification Route — M7
BFIU Circular No. 29 — Section 3.2

POST /api/v1/fingerprint/verify  — verify fingerprint against EC/Porichoy
POST /api/v1/fingerprint/demo    — set demo scenario (admin)
GET  /api/v1/fingerprint/status  — provider status
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.fingerprint_service import (
    verify_fingerprint, set_demo_scenario,
    PROVIDER, DEMO_SCENARIOS, _session_attempts,
    MAX_ATTEMPTS_PER_SESSION, FALLBACK_AFTER_SESSIONS,
)

router = APIRouter(prefix="/fingerprint", tags=["Fingerprint"])


class FingerprintRequest(BaseModel):
    session_id:      str
    nid_number:      str
    dob:             str              # DD/MM/YYYY
    fingerprint_b64: Optional[str] = ""   # Base64 WSQ or ISO template from scanner
    finger_position: str = "RIGHT_INDEX"  # RIGHT_INDEX / LEFT_INDEX / RIGHT_THUMB etc.


class DemoScenarioRequest(BaseModel):
    scenario: str   # MATCH / NO_MATCH / LOW_QUALITY / TIMEOUT


@router.post("/verify", summary="Verify fingerprint — BFIU §3.2")
async def verify(req: FingerprintRequest):
    return verify_fingerprint(
        session_id      = req.session_id,
        nid_number      = req.nid_number,
        dob             = req.dob,
        fingerprint_b64 = req.fingerprint_b64,
        finger_position = req.finger_position,
    )


@router.post("/demo", summary="Set demo scenario (admin only)")
async def set_scenario(req: DemoScenarioRequest):
    valid = list(DEMO_SCENARIOS.keys())
    if req.scenario not in valid:
        return {"error": f"Invalid scenario. Choose from: {valid}"}
    set_demo_scenario(req.scenario)
    return {"scenario": req.scenario, "active": True}


@router.get("/status", summary="Provider status and config")
async def status():
    return {
        "provider":              PROVIDER,
        "demo_scenarios":        list(DEMO_SCENARIOS.keys()),
        "max_attempts_session":  MAX_ATTEMPTS_PER_SESSION,
        "fallback_after":        FALLBACK_AFTER_SESSIONS,
        "hardware_slots": {
            "MANTRA":         "stub — install MantraFingerprint SDK",
            "NITGEN":         "stub — install Nitgen NBioBSP SDK",
            "DIGITALPERSONA": "stub — install DigitalPersona DPFJ SDK",
        },
        "bfiu_ref": "BFIU Circular No. 29 — Section 3.2",
    }
