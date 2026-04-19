# M35 — NID OCR Engine Work Log
**Date:** 2026-04-20
**Sprint:** Production Readiness — Phase B BFIU Compliance (P0)
**Status:** COMPLETE ✅

## Objective
Extract name (Bangla+English), DOB, father/mother name, address from NID card
image using Tesseract + OpenCV preprocessing. Mock fallback for dev/CI.

## Files Modified
| File | Change |
|------|--------|
| `app/services/nid_ocr_service.py` | Full M35 upgrade — OpenCV pipeline, quality check, multi-format parsing |

## Files Created
| File | Purpose |
|------|---------|
| `tests/test_m35_nid_ocr.py` | 34 tests (6 skipped when Tesseract unavailable) |

## OCR Pipeline
1. Decode base64 image → PIL Image
2. Quality check (brightness, sharpness, dimensions)
3. OpenCV preprocessing:
   - Grayscale conversion
   - Upscale if width < 1000px (improves Tesseract accuracy)
   - FastNlMeansDenoising
   - Adaptive threshold (handles uneven lighting)
   - Deskew (rotation correction)
4. Tesseract OCR (eng + ben+eng configs, PSM 6, OEM 3)
5. Regex field extraction
6. DOB normalisation → YYYY-MM-DD
7. NID number validation (10/13/17 digit formats)

## Fields Extracted
- `full_name_en` — English name
- `full_name_bn` — Bengali name
- `date_of_birth` — normalised YYYY-MM-DD
- `nid_number` — 10/13/17 digit
- `fathers_name_en` — Father's name
- `mothers_name_en` — Mother's name
- `address` — Present address
- `blood_group` — A/B/AB/O +/-

## Fallback Strategy
- Tesseract unavailable → mock result (realistic BD NID data)
- OpenCV unavailable → skip preprocessing, use PIL only
- Tesseract path auto-detected from known Windows locations

## Test Results
| Stage | Result |
|-------|--------|
| M35 unit tests | 34 passed, 6 skipped |
| Full suite | **980 passed, 0 failed, 7 skipped** |
