"""
M56 — Bangla Phonetic Name Matching — BFIU Circular No. 29 §3.2.4
Handles common Bengali name transliteration variants in Roman script.
Prevents false-negatives in UNSCR/PEP screening caused by spelling variation.

Examples caught:
  Rahman / Rahaman / Rehman / Rahmaan
  Mohammad / Mohammed / Muhammad / Md
  Hossain / Hussain / Hasan / Hassan
  Uddin / Uddin / Udden / Oddin
  Ullah / Ulla / Ola
  Khatun / Khatoon / Khatum
  Sheikh / Shaikh / Shaykh
  Chowdhury / Choudhury / Chaudhary
"""
import re
from typing import Callable


# ── Transliteration substitution rules ───────────────────────────────────
# Pass 1: full-word name canonicalization (before any consonant rules fire)
_NAME_RULES: list[tuple[str, str]] = [
    (r"\bRAHAMAN\b", "RAHMAN"),
    (r"\bREHMAN\b",  "RAHMAN"),
    (r"\bRAHMAAN\b", "RAHMAN"),
    (r"\bRAHEEM\b",  "RAHIM"),
    (r"\bMOHAMMAD\b","MUHAMMAD"),
    (r"\bMOHAMMED\b","MUHAMMAD"),
    (r"\bMOHAMAD\b", "MUHAMMAD"),
    (r"\bMAHAMMAD\b","MUHAMMAD"),
    (r"\bMEHAMMAD\b","MUHAMMAD"),
    (r"\bMD\b",      "MUHAMMAD"),
    (r"\bHOSSAIN\b", "HUSSAIN"),
    (r"\bHUSAIN\b",  "HUSSAIN"),
    (r"\bHASAN\b",   "HUSSAIN"),
    (r"\bHASSAN\b",  "HUSSAIN"),
    (r"\bHUSEN\b",   "HUSSAIN"),
    (r"\bUDDEN\b",   "UDDIN"),
    (r"\bODDIN\b",   "UDDIN"),
    (r"\bUDIN\b",    "UDDIN"),
    (r"\bULLA\b",    "ULLAH"),
    (r"\bKHATOON\b", "KHATUN"),
    (r"\bKHATUM\b",  "KHATUN"),
    (r"\bKHANUM\b",  "KHANAM"),
    (r"\bSHAIKH\b",  "SHEIKH"),
    (r"\bSHAYKH\b",  "SHEIKH"),
    (r"\bCHOUDHURY\b","CHOWDHURY"),
    (r"\bCHAUDHARY\b","CHOWDHURY"),
    (r"\bCHAUDHRY\b", "CHOWDHURY"),
    (r"\bCHOWDHRY\b", "CHOWDHURY"),
    (r"\bBEGOM\b",   "BEGUM"),
    (r"\bESLAM\b",   "ISLAM"),
    (r"\bMIAH\b",    "MIA"),
    (r"\bMEAH\b",    "MIA"),
    (r"\bALEE\b",    "ALI"),
]

# Pass 2: vowel/consonant normalization (applied after name rules)
_RULES: list[tuple[str, str]] = [
    (r"AA", "A"),
    (r"EE", "I"),
    (r"OO", "U"),
    (r"OU", "U"),
    (r"AE", "A"),
    (r"AI", "A"),
    (r"GH", "G"),
    (r"TH", "T"),
    (r"DH", "D"),
    (r"PH", "F"),
    (r"ZZ", "Z"),
    (r"CK", "K"),
    (r"QU", "K"),
    (r"Q",  "K"),
    (r"W",  "V"),
    (r"X",  "KS"),
    (r"(.)\1+", r"\1"),
]

# Compile once
_COMPILED_NAME: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern), repl)
    for pattern, repl in _NAME_RULES
]
_COMPILED: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern), repl)
    for pattern, repl in _RULES
]


def phonetic_normalize(name: str) -> str:
    """
    Normalize a Bengali personal name in Roman script to a canonical phonetic form.
    Two-pass: name canonicalization first, then consonant/vowel rules.
    """
    s = name.upper().strip()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Pass 1: full-word name rules
    for pattern, repl in _COMPILED_NAME:
        s = pattern.sub(repl, s)

    # Pass 2: vowel/consonant normalization
    for pattern, repl in _COMPILED:
        s = pattern.sub(repl, s)

    s = re.sub(r"\s+", " ", s).strip()
    return s


def phonetic_match_score(name1: str, name2: str) -> float:
    """
    Compute match score between two names using phonetic normalization.
    Returns 0.0-1.0. Combines token overlap on phonetic forms.
    """
    p1 = phonetic_normalize(name1)
    p2 = phonetic_normalize(name2)

    if p1 == p2:
        return 1.0

    t1 = set(p1.split())
    t2 = set(p2.split())
    if not t1 or not t2:
        return 0.0

    overlap = t1 & t2
    union   = t1 | t2
    return len(overlap) / len(union)


def enhanced_match_score(name1: str, name2: str,
                          base_scorer: Callable[[str, str], float] | None = None) -> float:
    """
    Combined score: max of base fuzzy score and phonetic score.
    Drop-in replacement for fuzzy_match_score with BD phonetic awareness.
    """
    phonetic = phonetic_match_score(name1, name2)
    if base_scorer:
        base = base_scorer(name1, name2)
        return max(phonetic, base)
    return phonetic
