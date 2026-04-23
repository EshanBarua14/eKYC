"""
Xpert Fintech eKYC Platform
Sanctions and Screening Engine - M9
BFIU Circular No. 29 - Section 3.2.2, 3.3.2, 5.1-5.3

Screening tiers:
- UNSCR: mandatory for ALL eKYC types - blocks on MATCH
- PEP/IP: mandatory for Regular eKYC only
- Adverse media: mandatory for Regular, optional for Simplified
- Exit list: institution-maintained, checked at every onboarding
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.services.bangla_phonetic import enhanced_match_score as _phonetic_score

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------
UNSCR_EXACT_MATCH_THRESHOLD  = 1.0   # Blocks account opening immediately
UNSCR_FUZZY_MATCH_THRESHOLD  = 0.85  # Flags for manual review
PEP_MATCH_THRESHOLD          = 0.80
ADVERSE_MEDIA_THRESHOLD      = 0.70

# ---------------------------------------------------------------------------
# Local UNSCR demo list (realistic BD-relevant entries)
# In prod: daily-refreshed from UN consolidated list via HTTPS
# ---------------------------------------------------------------------------
_UNSCR_LIST = [
    {"id": "UN-001", "name": "AL QAIDA",           "aliases": ["AL-QAEDA", "AQ"],          "type": "ENTITY"},
    {"id": "UN-002", "name": "DAESH",               "aliases": ["ISIS", "ISIL", "IS"],      "type": "ENTITY"},
    {"id": "UN-003", "name": "JAMAAT UL MUJAHIDEEN", "aliases": ["JMB", "JMJB"],             "type": "ENTITY"},
    {"id": "UN-004", "name": "HARAKAT UL JIHAD",    "aliases": ["HUJI"],                      "type": "ENTITY"},
    {"id": "UN-005", "name": "SANCTIONED PERSON ONE", "aliases": ["SP ONE", "S P ONE"],      "type": "INDIVIDUAL"},
    {"id": "UN-006", "name": "SANCTIONED PERSON TWO", "aliases": ["SP TWO"],                   "type": "INDIVIDUAL"},
    {"id": "UN-007", "name": "BLOCKED ENTITY BD",   "aliases": ["BEBD"],                      "type": "ENTITY"},
]

# ---------------------------------------------------------------------------
# Local PEP list (demo)
# In prod: sourced from BFIU official PEP list + commercial provider
# ---------------------------------------------------------------------------
_PEP_LIST = [
    {"id": "PEP-001", "name": "POLITICAL FIGURE ONE",  "role": "MINISTER",      "country": "BD"},
    {"id": "PEP-002", "name": "POLITICAL FIGURE TWO",  "role": "MP",            "country": "BD"},
    {"id": "PEP-003", "name": "SENIOR OFFICIAL THREE", "role": "SECRETARY",     "country": "BD"},
    {"id": "PEP-004", "name": "JUDGE FOUR",            "role": "CHIEF JUSTICE", "country": "BD"},
]

# ---------------------------------------------------------------------------
# Institution exit lists (per-institution, admin-maintained)
# ---------------------------------------------------------------------------
_EXIT_LISTS: dict = {}  # institution_id -> list of {name, reason, added_at}

# ---------------------------------------------------------------------------
# Fuzzy name matching (handles BD transliterations + edit distance)
# ---------------------------------------------------------------------------
def normalize_name(name: str) -> str:
    """Normalize name for comparison: uppercase, strip punctuation, collapse spaces."""
    name = name.upper().strip()
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def token_overlap_score(name1: str, name2: str) -> float:
    """Token-based overlap score (0.0-1.0)."""
    t1 = set(normalize_name(name1).split())
    t2 = set(normalize_name(name2).split())
    if not t1 or not t2:
        return 0.0
    overlap = t1 & t2
    union   = t1 | t2
    return len(overlap) / len(union)

def edit_distance_score(s1: str, s2: str) -> float:
    """Normalized edit distance score (0.0-1.0, higher = more similar)."""
    s1 = normalize_name(s1)
    s2 = normalize_name(s2)
    if not s1 or not s2:
        return 0.0
    # Simple edit distance
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    max_len = max(m, n)
    return 1.0 - (dp[m][n] / max_len) if max_len > 0 else 1.0

def fuzzy_match_score(name1: str, name2: str) -> float:
    """Combined score: phonetic (BD-aware) + token overlap + edit distance."""
    base = max(token_overlap_score(name1, name2), edit_distance_score(name1, name2))
    return _phonetic_score(name1, name2, base_scorer=lambda a,b: base)

# ---------------------------------------------------------------------------
# UNSCR screening
# ---------------------------------------------------------------------------
def screen_unscr(name: str) -> dict:
    """
    Screen name against UNSCR consolidated list.
    Returns verdict: CLEAR | MATCH | REVIEW
    MATCH -> blocks account opening immediately (BFIU mandatory)
    REVIEW -> flagged for manual checker review
    """
    name_normalized = normalize_name(name)
    matches = []

    for entry in _UNSCR_LIST:
        # Check primary name
        score = fuzzy_match_score(name, entry["name"])
        if score >= UNSCR_EXACT_MATCH_THRESHOLD:
            matches.append({"entry": entry, "score": score, "match_type": "EXACT"})
            continue
        if score >= UNSCR_FUZZY_MATCH_THRESHOLD:
            matches.append({"entry": entry, "score": score, "match_type": "FUZZY"})
            continue
        # Check aliases
        for alias in entry.get("aliases", []):
            alias_score = fuzzy_match_score(name, alias)
            if alias_score >= UNSCR_FUZZY_MATCH_THRESHOLD:
                matches.append({
                    "entry": entry, "score": alias_score,
                    "match_type": "ALIAS", "matched_alias": alias
                })
                break

    if not matches:
        return {
            "verdict":    "CLEAR",
            "name":       name,
            "matches":    [],
            "list_version": _get_list_version(),
            "screened_at": datetime.now(timezone.utc).isoformat(),
            "bfiu_ref":   "BFIU Circular No. 29 - Section 3.2.2",
        }

    best_match   = max(matches, key=lambda x: x["score"])
    exact_exists = any(m["match_type"] == "EXACT" for m in matches)
    verdict      = "MATCH" if exact_exists or best_match["score"] >= UNSCR_EXACT_MATCH_THRESHOLD else "REVIEW"

    return {
        "verdict":      verdict,
        "name":         name,
        "matches":      matches,
        "best_score":   best_match["score"],
        "list_version": _get_list_version(),
        "screened_at":  datetime.now(timezone.utc).isoformat(),
        "blocking":     verdict == "MATCH",
        "bfiu_ref":     "BFIU Circular No. 29 - Section 3.2.2",
    }

# ---------------------------------------------------------------------------
# PEP screening
# ---------------------------------------------------------------------------
def screen_pep(name: str) -> dict:
    """
    Screen name against PEP list.
    Mandatory for Regular eKYC only.
    Returns verdict: CLEAR | MATCH | REVIEW
    """
    matches = []

    for entry in _PEP_LIST:
        score = fuzzy_match_score(name, entry["name"])
        if score >= PEP_MATCH_THRESHOLD:
            matches.append({"entry": entry, "score": score})

    if not matches:
        return {
            "verdict":    "CLEAR",
            "name":       name,
            "matches":    [],
            "screened_at": datetime.now(timezone.utc).isoformat(),
            "bfiu_ref":   "BFIU Circular No. 29 - Section 4.2",
        }

    best = max(matches, key=lambda x: x["score"])
    return {
        "verdict":    "MATCH",
        "name":       name,
        "matches":    matches,
        "best_score": best["score"],
        "role":       best["entry"]["role"],
        "screened_at": datetime.now(timezone.utc).isoformat(),
        "edd_required": True,
        "bfiu_ref":   "BFIU Circular No. 29 - Section 4.2",
    }

# ---------------------------------------------------------------------------
# Adverse media screening
# ---------------------------------------------------------------------------
_ADVERSE_KEYWORDS = [
    "fraud", "money laundering", "terrorist", "corruption",
    "bribery", "sanction", "convicted", "arrested", "indicted",
    "financial crime", "embezzlement", "tax evasion",
]

def screen_adverse_media(name: str, kyc_type: str = "REGULAR") -> dict:
    """
    Screen for adverse media.
    In prod: queries configured news/crime database APIs.
    In dev: keyword simulation against demo adverse entries.
    """
    # Demo adverse media database
    _ADVERSE_DEMO = {
        "KARIM CORRUPT": ["Convicted of fraud in 2023", "Money laundering case pending"],
        "BAD ACTOR BD":  ["Terrorist financing investigation"],
    }

    name_upper = name.upper()
    hits = []

    for bad_name, articles in _ADVERSE_DEMO.items():
        score = fuzzy_match_score(name, bad_name)
        if score >= ADVERSE_MEDIA_THRESHOLD:
            hits.extend([{"headline": a, "score": score} for a in articles])

    verdict = "CLEAR" if not hits else "FLAGGED"
    return {
        "verdict":      verdict,
        "name":         name,
        "kyc_type":     kyc_type,
        "hits":         hits,
        "hit_count":    len(hits),
        "edd_required": verdict == "FLAGGED",
        "screened_at":  datetime.now(timezone.utc).isoformat(),
        "bfiu_ref":     "BFIU Circular No. 29 - Section 5.3",
    }

# ---------------------------------------------------------------------------
# Exit list management
# ---------------------------------------------------------------------------
def add_to_exit_list(institution_id: str, name: str, reason: str) -> dict:
    """Add a name to institution exit list."""
    if institution_id not in _EXIT_LISTS:
        _EXIT_LISTS[institution_id] = []
    entry = {
        "id":         str(uuid.uuid4()),
        "name":       name,
        "reason":     reason,
        "added_at":   datetime.now(timezone.utc).isoformat(),
        "added_by":   "system",
    }
    _EXIT_LISTS[institution_id].append(entry)
    return entry

def screen_exit_list(name: str, institution_id: str) -> dict:
    """Check name against institution exit list."""
    exit_list = _EXIT_LISTS.get(institution_id, [])
    matches   = []

    for entry in exit_list:
        score = fuzzy_match_score(name, entry["name"])
        if score >= UNSCR_FUZZY_MATCH_THRESHOLD:
            matches.append({"entry": entry, "score": score})

    verdict = "MATCH" if matches else "CLEAR"
    return {
        "verdict":    verdict,
        "name":       name,
        "matches":    matches,
        "screened_at": datetime.now(timezone.utc).isoformat(),
        "blocking":   verdict == "MATCH",
        "bfiu_ref":   "BFIU Circular No. 29 - Section 5.1",
    }

# ---------------------------------------------------------------------------
# Full screening (run all applicable checks)
# ---------------------------------------------------------------------------
def run_full_screening(
    name:           str,
    kyc_type:       str = "SIMPLIFIED",
    institution_id: str = "DEMO",
) -> dict:
    """
    Run all applicable screening checks based on eKYC type.
    SIMPLIFIED: UNSCR + Exit list
    REGULAR:    UNSCR + PEP + Adverse media + Exit list
    Returns combined verdict: CLEAR | REVIEW | BLOCKED
    """
    results = {}

    # UNSCR - mandatory for all
    results["unscr"] = screen_unscr(name)

    # Exit list - mandatory for all
    results["exit_list"] = screen_exit_list(name, institution_id)

    # Regular eKYC only
    if kyc_type.upper() == "REGULAR":
        results["pep"]           = screen_pep(name)
        results["adverse_media"] = screen_adverse_media(name, kyc_type)

    # Determine combined verdict
    blocked = (
        results["unscr"]["verdict"] == "MATCH" or
        results["exit_list"]["verdict"] == "MATCH"
    )
    review = (
        results["unscr"]["verdict"] == "REVIEW" or
        results.get("pep", {}).get("verdict") == "MATCH" or
        results.get("adverse_media", {}).get("verdict") == "FLAGGED"
    )

    combined = "BLOCKED" if blocked else ("REVIEW" if review else "CLEAR")
    edd_required = combined in ["BLOCKED", "REVIEW"]

    return {
        "combined_verdict": combined,
        "name":             name,
        "kyc_type":         kyc_type,
        "edd_required":     edd_required,
        "blocking":         blocked,
        "results":          results,
        "screened_at":      datetime.now(timezone.utc).isoformat(),
        "bfiu_ref":         "BFIU Circular No. 29 - Section 5",
    }

def _get_list_version() -> str:
    """Return current list version (date-stamped in prod)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d") + "-DEMO"

def reset_exit_lists():
    """Clear all exit lists (for testing)."""
    _EXIT_LISTS.clear()
