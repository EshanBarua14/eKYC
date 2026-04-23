"""M56 — Bangla Phonetic Name Matching Tests — BFIU Circular No. 29 §3.2.4"""
from app.services.bangla_phonetic import phonetic_normalize, phonetic_match_score, enhanced_match_score
from app.services.screening_service import fuzzy_match_score


# ── phonetic_normalize ────────────────────────────────────────────────────
def test_rahman_variants_normalize_same():
    assert phonetic_normalize("Rahman") == phonetic_normalize("Rahaman")
    assert phonetic_normalize("Rehman") == phonetic_normalize("Rahmaan")

def test_mohammad_variants_normalize_same():
    assert phonetic_normalize("Mohammad") == phonetic_normalize("Mohammed")
    assert phonetic_normalize("Muhammad") == phonetic_normalize("Mohamad")

def test_hossain_variants_normalize_same():
    assert phonetic_normalize("Hossain") == phonetic_normalize("Hussain")
    assert phonetic_normalize("Hasan")   == phonetic_normalize("Hassan")

def test_uddin_variants_normalize_same():
    assert phonetic_normalize("Uddin") == phonetic_normalize("Udden")
    assert phonetic_normalize("Uddin") == phonetic_normalize("Oddin")

def test_chowdhury_variants_normalize_same():
    assert phonetic_normalize("Chowdhury") == phonetic_normalize("Choudhury")
    assert phonetic_normalize("Chowdhury") == phonetic_normalize("Chaudhary")

def test_sheikh_variants_normalize_same():
    assert phonetic_normalize("Sheikh") == phonetic_normalize("Shaikh")
    assert phonetic_normalize("Sheikh") == phonetic_normalize("Shaykh")

def test_khatun_variants_normalize_same():
    assert phonetic_normalize("Khatun") == phonetic_normalize("Khatoon")
    assert phonetic_normalize("Khatun") == phonetic_normalize("Khatum")

def test_unrelated_names_differ():
    assert phonetic_normalize("Rahman") != phonetic_normalize("Chowdhury")


# ── phonetic_match_score ──────────────────────────────────────────────────
def test_rahman_rahaman_score_1():
    assert phonetic_match_score("Rahman", "Rahaman") == 1.0

def test_mohammad_ali_mohammed_ali_score_1():
    assert phonetic_match_score("Mohammad Ali", "Mohammed Ali") == 1.0

def test_hossain_hussain_score_1():
    assert phonetic_match_score("Hossain", "Hussain") == 1.0

def test_unrelated_score_low():
    assert phonetic_match_score("Rahman", "Chowdhury") < 0.5

def test_exact_match_score_1():
    assert phonetic_match_score("Abdul Karim", "Abdul Karim") == 1.0


# ── enhanced_match_score ──────────────────────────────────────────────────
def test_enhanced_score_higher_than_naive():
    from app.services.screening_service import token_overlap_score
    naive = token_overlap_score("Mohammad Ali Hossain", "Mohammed Ali Hussain")
    enhanced = enhanced_match_score("Mohammad Ali Hossain", "Mohammed Ali Hussain")
    assert enhanced >= naive

def test_enhanced_score_rahaman_rahman():
    score = enhanced_match_score("Rahaman", "Rahman")
    assert score >= 0.9


# ── Integration: fuzzy_match_score now BD-aware ───────────────────────────
def test_fuzzy_match_rahman_rahaman():
    assert fuzzy_match_score("Rahman", "Rahaman") >= 0.9

def test_fuzzy_match_mohammad_mohammed():
    assert fuzzy_match_score("Mohammad Ali", "Mohammed Ali") >= 0.9

def test_fuzzy_match_chowdhury_choudhury():
    assert fuzzy_match_score("Chowdhury", "Choudhury") >= 0.9

def test_fuzzy_match_unrelated_stays_low():
    assert fuzzy_match_score("Rahman", "Chowdhury") < 0.6

def test_screening_catches_rahman_variant():
    from app.services.screening_service import screen_pep
    # Add a PEP with Rahman spelling, query with Rahaman
    from app.services import screening_service
    original = screening_service._PEP_LIST[:]
    screening_service._PEP_LIST.append({
        "id": "PEP-TEST-01", "name": "RAHMAN TEST PEP",
        "role": "MINISTER", "country": "BD"
    })
    try:
        result = screen_pep("Rahaman Test Pep")
        assert result["verdict"] == "MATCH", f"Expected MATCH, got {result['verdict']}"
    finally:
        screening_service._PEP_LIST[:] = original
