"""
Face Verification Route
BFIU Circular No. 29 — Section 3.3
POST /api/v1/face/verify
"""
import time
from fastapi import APIRouter
from app.models.schemas import VerifyRequest, VerifyResponse
from app.services.image_utils import b64_to_numpy, numpy_to_b64, detect_face
from app.services.liveness import run_liveness_checks
from app.services.face_match import compare_faces, get_verdict
from app.core.config import settings

router = APIRouter(prefix="/face", tags=["Face Verification"])


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify NID face against live selfie",
    description="""
    Accepts a Bangladesh NID photo and a live webcam image (both base64).
    Performs:
    - Face detection on both images
    - Liveness checks per BFIU Annexure-2
    - Biometric face matching per Section 3.3
    Returns a full structured verification report.
    """,
)
async def verify_face(req: VerifyRequest):
    start = time.time()

    # Decode images
    nid_img  = b64_to_numpy(req.nid_image_b64)
    live_img = b64_to_numpy(req.live_image_b64)

    # Detect faces
    nid_face,  nid_coords  = detect_face(nid_img)
    live_face, live_coords = detect_face(live_img)

    nid_found  = nid_face is not None and nid_face.size > 0
    live_found = live_face is not None and live_face.size > 0

    # Liveness checks
    liveness = run_liveness_checks(live_img, live_coords)

    # Face matching
    match_scores = None
    confidence   = 0.0
    if nid_found and live_found:
        match_scores = compare_faces(nid_face, live_face)
        confidence   = match_scores["confidence"]

    # Verdict
    verdict, reason = get_verdict(nid_found, live_found, liveness["overall_pass"], confidence)

    return {
        "session_id":     req.session_id,
        "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "processing_ms":  round((time.time() - start) * 1000, 1),
        "verdict":        verdict,
        "verdict_reason": reason,
        "confidence":     confidence,
        "faces": {
            "nid_face_detected":  nid_found,
            "live_face_detected": live_found,
            "nid_face_coords":    nid_coords,
            "live_face_coords":   live_coords,
            "nid_face_preview":   numpy_to_b64(nid_face)  if nid_found  else None,
            "live_face_preview":  numpy_to_b64(live_face) if live_found else None,
        },
        "liveness":    liveness,
        "match_scores": match_scores,
        "bfiu_ref": {
            "guideline": settings.BFIU_GUIDELINE,
            "section":   settings.BFIU_SECTION,
            "annexure":  settings.BFIU_ANNEXURE,
        },
    }
