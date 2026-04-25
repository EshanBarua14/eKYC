"""
M85: Composite Identity Score — BFIU Circular No. 29 Annexure-2
Combines face verification confidence + NID match + DOB match
into a single 0–100 identity score with PASS/REVIEW/FAIL verdict.

Score components:
  Face similarity   : 50% weight (biometric — strongest signal)
  NID match         : 30% weight (authoritative government record)
  DOB match         : 20% weight (secondary identity anchor)

Thresholds (aligned to BFIU Annexure-2 face verify thresholds):
  PASS   : composite >= 70  (high confidence — auto-approve)
  REVIEW : composite >= 45  (marginal — checker review required)
  FAIL   : composite <  45  (low confidence — reject)

BFIU §3.2: face match >= 45% confidence required for MATCHED verdict.
Composite score adds NID+DOB layers on top for stronger identity proof.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

log = logging.getLogger(__name__)

BST = timezone(timedelta(hours=6))

# ── Weights ──────────────────────────────────────────────────────────────────
WEIGHT_FACE = 0.50
WEIGHT_NID  = 0.30
WEIGHT_DOB  = 0.20

# ── Thresholds ───────────────────────────────────────────────────────────────
THRESHOLD_PASS   = 70.0   # composite score → PASS
THRESHOLD_REVIEW = 45.0   # composite score → REVIEW
# below THRESHOLD_REVIEW → FAIL

# ── Individual component minimums (hard floors) ──────────────────────────────
MIN_FACE_FOR_PASS   = 0.45   # BFIU Annexure-2 minimum face confidence
MIN_FACE_FOR_REVIEW = 0.30   # below this = FAIL regardless of composite


@dataclass
class IdentityScoreInput:
    """
    All inputs required to compute composite identity score.

    face_confidence : float 0.0–1.0 — output of face_match service
    nid_matched     : bool  — NID number verified against EC database
    dob_matched     : bool  — Date of birth matched between OCR and EC record
    nid_ocr_confidence : float 0.0–1.0 — OCR extraction confidence (optional)
    session_id      : str  — for audit logging
    """
    face_confidence:     float
    nid_matched:         bool
    dob_matched:         bool
    nid_ocr_confidence:  float = 1.0   # default: assume OCR succeeded
    session_id:          str   = ""
    kyc_type:            str   = "SIMPLIFIED"


@dataclass
class IdentityScoreResult:
    """Output of composite identity scoring."""
    composite_score:    float          # 0–100
    verdict:            str            # PASS | REVIEW | FAIL
    face_score:         float          # 0–100 (face_confidence * 100)
    nid_score:          float          # 0 or 100
    dob_score:          float          # 0 or 100
    weighted_face:      float          # contribution to composite
    weighted_nid:       float          # contribution to composite
    weighted_dob:       float          # contribution to composite
    face_confidence_raw: float         # original 0–1 input
    hard_floor_applied: bool           # True if face floor overrode composite
    bfiu_ref:           str = "BFIU Circular No. 29 Annexure-2"
    computed_at_bst:    str = ""
    session_id:         str = ""
    details:            dict = field(default_factory=dict)


def compute_composite_score(inp: IdentityScoreInput) -> IdentityScoreResult:
    """
    Compute composite identity score from face + NID + DOB signals.

    Hard floor rules (BFIU §3.2):
      - face_confidence < 0.30 → FAIL immediately (no composite calc)
      - face_confidence < 0.45 → cap verdict at REVIEW (cannot PASS)
      - nid_matched = False AND dob_matched = False → cap at REVIEW

    Returns IdentityScoreResult with full audit trail.
    """
    bst_now = datetime.now(BST).strftime("%Y-%m-%d %H:%M:%S BST")
    hard_floor = False

    # ── Component scores (0–100) ─────────────────────────────────────────────
    face_score = round(float(inp.face_confidence) * 100, 2)
    nid_score  = 100.0 if inp.nid_matched else 0.0
    dob_score  = 100.0 if inp.dob_matched else 0.0

    # ── Weighted contributions ───────────────────────────────────────────────
    w_face = round(face_score * WEIGHT_FACE, 4)
    w_nid  = round(nid_score  * WEIGHT_NID,  4)
    w_dob  = round(dob_score  * WEIGHT_DOB,  4)

    composite = round(w_face + w_nid + w_dob, 2)

    # ── Hard floor: face below absolute minimum → FAIL ───────────────────────
    if inp.face_confidence < MIN_FACE_FOR_REVIEW:
        verdict = "FAIL"
        hard_floor = True
        log.warning(
            "[M85] FAIL — face_confidence=%.3f below minimum %.2f — session=%s",
            inp.face_confidence, MIN_FACE_FOR_REVIEW, inp.session_id
        )
    # ── Hard floor: face below BFIU minimum → cap at REVIEW ──────────────────
    elif inp.face_confidence < MIN_FACE_FOR_PASS:
        verdict = "REVIEW"
        hard_floor = True
        log.info(
            "[M85] REVIEW (face floor) — face_confidence=%.3f < %.2f — session=%s",
            inp.face_confidence, MIN_FACE_FOR_PASS, inp.session_id
        )
    # ── Hard floor: neither NID nor DOB matched → cap at REVIEW ──────────────
    elif not inp.nid_matched and not inp.dob_matched:
        verdict = "REVIEW"
        hard_floor = True
        log.info(
            "[M85] REVIEW (identity floor) — nid=False dob=False — session=%s",
            inp.session_id
        )
    # ── Normal composite thresholds ───────────────────────────────────────────
    elif composite >= THRESHOLD_PASS:
        verdict = "PASS"
    elif composite >= THRESHOLD_REVIEW:
        verdict = "REVIEW"
    else:
        verdict = "FAIL"

    log.info(
        "[M85] composite=%.2f verdict=%s face=%.2f nid=%s dob=%s session=%s",
        composite, verdict, face_score,
        inp.nid_matched, inp.dob_matched, inp.session_id
    )

    return IdentityScoreResult(
        composite_score=composite,
        verdict=verdict,
        face_score=face_score,
        nid_score=nid_score,
        dob_score=dob_score,
        weighted_face=w_face,
        weighted_nid=w_nid,
        weighted_dob=w_dob,
        face_confidence_raw=inp.face_confidence,
        hard_floor_applied=hard_floor,
        computed_at_bst=bst_now,
        session_id=inp.session_id,
        details={
            "weights": {
                "face": WEIGHT_FACE,
                "nid":  WEIGHT_NID,
                "dob":  WEIGHT_DOB,
            },
            "thresholds": {
                "pass":   THRESHOLD_PASS,
                "review": THRESHOLD_REVIEW,
                "min_face_pass":   MIN_FACE_FOR_PASS,
                "min_face_review": MIN_FACE_FOR_REVIEW,
            },
            "inputs": {
                "face_confidence":    inp.face_confidence,
                "nid_matched":        inp.nid_matched,
                "dob_matched":        inp.dob_matched,
                "nid_ocr_confidence": inp.nid_ocr_confidence,
                "kyc_type":           inp.kyc_type,
            },
        },
    )


def score_from_verification_result(
    face_confidence: float,
    nid_check: dict,
    session_id: str = "",
    kyc_type: str = "SIMPLIFIED",
) -> IdentityScoreResult:
    """
    Convenience wrapper — accepts output dicts from existing services.

    nid_check: dict from nid_api_client._verify_live() — contains:
      checks.dob.matched, nid_matched, etc.
    """
    nid_matched = (
        nid_check.get("nid_matched", False) or
        nid_check.get("matched", False) or
        nid_check.get("status") == "MATCHED"
    )
    dob_check = nid_check.get("checks", {}).get("dob", {})
    dob_matched = dob_check.get("matched", False) if isinstance(dob_check, dict) else False

    return compute_composite_score(IdentityScoreInput(
        face_confidence=float(face_confidence),
        nid_matched=bool(nid_matched),
        dob_matched=bool(dob_matched),
        session_id=session_id,
        kyc_type=kyc_type,
    ))
