# M56 — Bangla Phonetic Name Matching
**Date:** 2026-04-24
**Sprint:** BFIU Circular No. 29 Compliance
**Status:** COMPLETE ✅

## Objective
Two-pass Bangla phonetic normalizer wired into fuzzy_match_score()
for UNSCR/sanctions screening per BFIU Circular No. 29 §3.2.4.

## Files
| File | Purpose |
|------|---------|
| `app/services/bangla_phonetic.py` | Two-pass phonetic normalizer |
| `app/services/screening_service.py` | enhanced_match_score() → fuzzy_match_score() |
| `tests/test_m56_bangla_phonetic.py` | 20 tests |

## Test Coverage
- Normalization: Rahman/Rahaman, Mohammad/Mohammed, Hossain/Hussain,
  Uddin/Uddin, Chowdhury/Choudhury, Sheikh/Shaikh, Khatun/Khatoon
- Scoring: exact=1.0, variants≥0.85, unrelated<0.5
- Integration: screening_service catches Rahman variant in UNSCR list

## Test Results
- M56 suite: 20 passed
- Full suite: 1221 passed, 0 failed

## BFIU Reference
§3.2.4 — Name matching must handle Bangla transliteration variants
and romanization differences.
