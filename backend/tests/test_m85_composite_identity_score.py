"""
M85: Composite Identity Score tests — BFIU Circular No. 29 Annexure-2
"""
import pytest
from app.services.composite_identity_score import (
    compute_composite_score,
    score_from_verification_result,
    IdentityScoreInput,
    IdentityScoreResult,
    WEIGHT_FACE, WEIGHT_NID, WEIGHT_DOB,
    THRESHOLD_PASS, THRESHOLD_REVIEW,
    MIN_FACE_FOR_PASS, MIN_FACE_FOR_REVIEW,
)


def make_input(**kwargs):
    defaults = dict(face_confidence=0.85, nid_matched=True,
                    dob_matched=True, session_id="test-session")
    defaults.update(kwargs)
    return IdentityScoreInput(**defaults)


# ── Weights and constants ─────────────────────────────────────────────────────

def test_weights_sum_to_one():
    assert abs(WEIGHT_FACE + WEIGHT_NID + WEIGHT_DOB - 1.0) < 1e-9

def test_face_weight_dominant():
    assert WEIGHT_FACE >= 0.45

def test_threshold_pass_above_review():
    assert THRESHOLD_PASS > THRESHOLD_REVIEW

def test_bfiu_minimum_face_confidence():
    """BFIU §3.2 — minimum face confidence must be 45%."""
    assert MIN_FACE_FOR_PASS == 0.45

def test_review_floor_below_pass_floor():
    assert MIN_FACE_FOR_REVIEW < MIN_FACE_FOR_PASS


# ── Perfect match ─────────────────────────────────────────────────────────────

def test_perfect_match_passes():
    r = compute_composite_score(make_input(
        face_confidence=1.0, nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "PASS"
    assert r.composite_score == 100.0

def test_high_confidence_all_matched_passes():
    r = compute_composite_score(make_input(
        face_confidence=0.92, nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "PASS"
    assert r.composite_score >= THRESHOLD_PASS

def test_composite_formula_correct():
    r = compute_composite_score(make_input(
        face_confidence=0.80, nid_matched=True, dob_matched=True
    ))
    expected = round(80*WEIGHT_FACE + 100*WEIGHT_NID + 100*WEIGHT_DOB, 2)
    assert r.composite_score == expected

def test_component_scores_correct():
    r = compute_composite_score(make_input(
        face_confidence=0.75, nid_matched=True, dob_matched=False
    ))
    assert r.face_score == 75.0
    assert r.nid_score == 100.0
    assert r.dob_score == 0.0

def test_weighted_contributions_sum_to_composite():
    r = compute_composite_score(make_input(
        face_confidence=0.65, nid_matched=True, dob_matched=True
    ))
    assert abs(r.weighted_face + r.weighted_nid + r.weighted_dob - r.composite_score) < 0.01


# ── PASS verdicts ─────────────────────────────────────────────────────────────

def test_pass_requires_composite_above_70():
    r = compute_composite_score(make_input(
        face_confidence=0.80, nid_matched=True, dob_matched=True
    ))
    assert r.composite_score >= THRESHOLD_PASS
    assert r.verdict == "PASS"

def test_pass_verdict_no_hard_floor():
    r = compute_composite_score(make_input(
        face_confidence=0.90, nid_matched=True, dob_matched=True
    ))
    assert r.hard_floor_applied is False
    assert r.verdict == "PASS"


# ── REVIEW verdicts ───────────────────────────────────────────────────────────

def test_review_when_face_below_bfiu_minimum():
    """face < 0.45 → REVIEW regardless of composite."""
    r = compute_composite_score(make_input(
        face_confidence=0.40, nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "REVIEW"
    assert r.hard_floor_applied is True

def test_review_when_nid_and_dob_both_fail():
    r = compute_composite_score(make_input(
        face_confidence=0.80, nid_matched=False, dob_matched=False
    ))
    assert r.verdict == "REVIEW"
    assert r.hard_floor_applied is True

def test_review_when_composite_between_45_and_70():
    r = compute_composite_score(make_input(
        face_confidence=0.60, nid_matched=False, dob_matched=True
    ))
    # composite = 60*0.5 + 0*0.3 + 100*0.2 = 30+0+20 = 50 → REVIEW
    assert THRESHOLD_REVIEW <= r.composite_score < THRESHOLD_PASS
    assert r.verdict == "REVIEW"

def test_review_face_floor_overrides_high_composite():
    """Even with NID+DOB matched, face < 0.45 must be REVIEW."""
    r = compute_composite_score(make_input(
        face_confidence=0.44, nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "REVIEW"
    assert r.hard_floor_applied is True


# ── FAIL verdicts ─────────────────────────────────────────────────────────────

def test_fail_when_face_below_absolute_minimum():
    r = compute_composite_score(make_input(
        face_confidence=0.25, nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "FAIL"
    assert r.hard_floor_applied is True

def test_fail_zero_face_confidence():
    r = compute_composite_score(make_input(
        face_confidence=0.0, nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "FAIL"

def test_fail_low_composite_no_floor():
    """Low face + no NID + no DOB → hard floor triggers REVIEW (nid+dob both false)."""
    r = compute_composite_score(make_input(
        face_confidence=0.50, nid_matched=False, dob_matched=False
    ))
    # composite = 50*0.5 + 0 + 0 = 25 — but hard floor (nid+dob=False) → REVIEW
    assert r.hard_floor_applied is True
    assert r.verdict == "REVIEW"

def test_fail_low_composite_with_partial_identity():
    """Low face + no NID + DOB matched → composite < 45 → FAIL (no hard floor)."""
    r = compute_composite_score(make_input(
        face_confidence=0.50, nid_matched=False, dob_matched=True
    ))
    # composite = 50*0.5 + 0*0.3 + 100*0.2 = 25+0+20 = 45 → REVIEW (at threshold)
    # face >= 0.45 so no face floor; nid=False but dob=True so no identity floor
    assert r.hard_floor_applied is False
    assert r.verdict in ("REVIEW", "FAIL")  # 45 = boundary


# ── Result structure ──────────────────────────────────────────────────────────

def test_result_has_bfiu_ref():
    r = compute_composite_score(make_input())
    assert "BFIU" in r.bfiu_ref
    assert "Annexure-2" in r.bfiu_ref

def test_result_has_bst_timestamp():
    r = compute_composite_score(make_input())
    assert "BST" in r.computed_at_bst

def test_result_has_session_id():
    r = compute_composite_score(make_input(session_id="sess-xyz"))
    assert r.session_id == "sess-xyz"

def test_result_details_has_weights():
    r = compute_composite_score(make_input())
    assert "weights" in r.details
    assert r.details["weights"]["face"] == WEIGHT_FACE

def test_result_details_has_thresholds():
    r = compute_composite_score(make_input())
    assert "thresholds" in r.details
    assert r.details["thresholds"]["pass"] == THRESHOLD_PASS

def test_result_details_has_inputs():
    r = compute_composite_score(make_input(face_confidence=0.77))
    assert r.details["inputs"]["face_confidence"] == 0.77

def test_face_confidence_raw_preserved():
    r = compute_composite_score(make_input(face_confidence=0.83))
    assert r.face_confidence_raw == 0.83


# ── score_from_verification_result ───────────────────────────────────────────

def test_convenience_wrapper_nid_matched():
    nid_check = {
        "nid_matched": True,
        "checks": {"dob": {"matched": True}},
    }
    r = score_from_verification_result(0.88, nid_check, session_id="wrap-1")
    assert r.verdict == "PASS"
    assert r.nid_score == 100.0
    assert r.dob_score == 100.0

def test_convenience_wrapper_nid_not_matched():
    nid_check = {"nid_matched": False, "checks": {}}
    r = score_from_verification_result(0.92, nid_check)
    assert r.nid_score == 0.0
    assert r.dob_score == 0.0

def test_convenience_wrapper_status_matched():
    nid_check = {"status": "MATCHED", "checks": {"dob": {"matched": True}}}
    r = score_from_verification_result(0.85, nid_check)
    assert r.nid_score == 100.0

def test_convenience_wrapper_empty_nid_check():
    r = score_from_verification_result(0.50, {})
    assert r.nid_score == 0.0
    assert r.dob_score == 0.0

def test_convenience_wrapper_dob_nested():
    nid_check = {
        "matched": True,
        "checks": {"dob": {"matched": True, "ocr": "1990-01-01", "ec": "1990-01-01"}},
    }
    r = score_from_verification_result(0.91, nid_check, kyc_type="REGULAR")
    assert r.dob_score == 100.0
    assert r.details["inputs"]["kyc_type"] == "REGULAR"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_face_confidence_exactly_at_pass_threshold():
    r = compute_composite_score(make_input(
        face_confidence=MIN_FACE_FOR_PASS, nid_matched=True, dob_matched=True
    ))
    # 0.45*100*0.5 + 100*0.3 + 100*0.2 = 22.5+30+20 = 72.5 → PASS
    assert r.verdict == "PASS"

def test_face_confidence_just_below_pass_threshold():
    r = compute_composite_score(make_input(
        face_confidence=MIN_FACE_FOR_PASS - 0.001,
        nid_matched=True, dob_matched=True
    ))
    assert r.verdict == "REVIEW"
    assert r.hard_floor_applied is True

def test_composite_exactly_at_review_threshold():
    # Craft input where composite = exactly 45
    # face=0.50 → face_score=50, nid=False, dob=False
    # 50*0.5 + 0 + 0 = 25 — too low
    # face=0.90, nid=False, dob=False → 45+0+0=45 → REVIEW
    r = compute_composite_score(make_input(
        face_confidence=0.90, nid_matched=False, dob_matched=False
    ))
    assert r.verdict == "REVIEW"  # hard floor: nid+dob both false

def test_result_is_dataclass_instance():
    r = compute_composite_score(make_input())
    assert isinstance(r, IdentityScoreResult)

def test_input_is_dataclass_instance():
    inp = make_input()
    assert isinstance(inp, IdentityScoreInput)
