"""
Pydantic request/response schemas
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any

# ── Requests ─────────────────────────────────────────────

class VerifyRequest(BaseModel):
    nid_image_b64:  str
    live_image_b64: str
    session_id:     str = "default"

# ── Sub-responses ─────────────────────────────────────────

class FaceCoords(BaseModel):
    x: int
    y: int
    w: int
    h: int

class FaceResult(BaseModel):
    nid_face_detected:  bool
    live_face_detected: bool
    nid_face_coords:    Optional[FaceCoords]
    live_face_coords:   Optional[FaceCoords]
    nid_face_preview:   Optional[str]
    live_face_preview:  Optional[str]

class LivenessCheck(BaseModel):
    label: str
    pass_:  bool
    value:  Any

    class Config:
        populate_by_name = True

class LivenessResult(BaseModel):
    lighting:     Dict[str, Any]
    sharpness:    Dict[str, Any]
    resolution:   Dict[str, Any]
    face_size:    Dict[str, Any]
    overall_pass: bool
    score:        int
    max_score:    int

class MatchScores(BaseModel):
    histogram_score: float
    feature_score:   float
    pixel_score:     float
    confidence:      float

class BFIURef(BaseModel):
    guideline: str
    section:   str
    annexure:  str

# ── Main Response ─────────────────────────────────────────

class VerifyResponse(BaseModel):
    session_id:     str
    timestamp:      str
    processing_ms:  float
    verdict:        str   # MATCHED | REVIEW | FAILED
    verdict_reason: str
    confidence:     float
    faces:          FaceResult
    liveness:       LivenessResult
    match_scores:   Optional[MatchScores]
    bfiu_ref:       BFIURef

class HealthResponse(BaseModel):
    status:  str
    service: str
    version: str
