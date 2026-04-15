# Xpert Fintech eKYC — Work Log
**BFIU Circular No. 29 Compliant**

---

## Project Summary
Full-stack eKYC (Electronic Know Your Customer) module for Bangladesh
Insurance Companies and Capital Market Intermediaries (CMIs).

| Item            | Detail                                      |
|-----------------|---------------------------------------------|
| Regulation      | BFIU Circular No. 29 — March 30, 2026       |
| Deadline        | December 31, 2026                           |
| Backend         | Python 3.14 · FastAPI · OpenCV · MediaPipe  |
| Frontend        | React 19 · Vite · react-webcam              |
| AI Models       | OpenCV DNN (ResNet SSD) · MediaPipe FaceLandmarker |
| Test Coverage   | 15/15 passing (100%)                        |

---

## API Endpoints

| Method | Endpoint                  | Description                        |
|--------|---------------------------|------------------------------------|
| GET    | /health                   | Service health check               |
| POST   | /api/v1/face/verify       | NID vs live face verification      |
| POST   | /api/v1/ai/analyze        | Full AI face analysis (478 pts)    |
| POST   | /api/v1/ai/challenge      | Single liveness challenge check    |
| POST   | /api/v1/ai/scan-nid       | NID card scan quality check        |

---

## Architecture
---

## BFIU Compliance Coverage

| Requirement                          | Section        | Status |
|--------------------------------------|----------------|--------|
| Face-matching onboarding             | §3.3           | ✅     |
| High-resolution camera               | §3.3.1         | ✅     |
| Adequate white lighting              | Annexure-2b    | ✅     |
| White background guidance            | Annexure-2c    | ✅     |
| No glare on NID                      | Annexure-2d    | ✅     |
| Full front face visible              | Annexure-2e    | ✅     |
| Depth sensing (3D human body)        | Annexure-2g    | ✅     |
| Self check-in for face matching      | §2.2(b)        | ✅     |
| 10 attempts/session limit            | §3.3           | ✅     |
| Sanctions screening (UNSCR)          | §3.3.2         | 🔜     |
| IP/PEP screening                     | §4.2           | 🔜     |
| Risk grading engine                  | §6.3           | 🔜     |
| Periodic KYC lifecycle               | §5.7           | 🔜     |
| Audit trail                          | §3.3.3         | 🔜     |
| Data residency enforcement           | §3.3.5         | 🔜     |

---

## Face Matching Algorithm

| Method         | Weight | Purpose                              |
|----------------|--------|--------------------------------------|
| SSIM           | 35%    | Structural similarity (best for NID) |
| Histogram      | 30%    | Color/tone correlation after CLAHE   |
| ORB Features   | 25%    | Keypoint matching (Lowe's ratio)     |
| Pixel          | 10%    | Supporting signal                    |

**Thresholds:**
- MATCHED : confidence ≥ 45%
- REVIEW  : confidence ≥ 30%
- FAILED  : confidence < 30%

---

## Face Detection Pipeline

1. **DNN (ResNet SSD)** — primary, works on NID document photos
2. **Haar Cascade** — fallback for DNN misses
3. **Center Crop** — final fallback for NID cards where face detection fails

---

## Liveness Challenges (Annexure-2)

| Step | Challenge     | Detection Method              |
|------|---------------|-------------------------------|
| 1    | Look straight | Head yaw/pitch < 15°          |
| 2    | Blink eyes    | MediaPipe blendshape EAR      |
| 3    | Turn left     | Yaw < -15°                    |
| 4    | Turn right    | Yaw > +15°                    |
| 5    | Smile         | Mouth corner lift ratio       |

---

## Session Log

| Date       | Action                                      |
|------------|---------------------------------------------|
| 2026-04-15 | Project initialized                         |
| 2026-04-15 | Backend modular API structure created       |
| 2026-04-15 | DNN face detector integrated                |
| 2026-04-15 | NID-aware face matching algorithm built     |
| 2026-04-15 | MediaPipe liveness challenges integrated    |
| 2026-04-15 | Frontend 3-step flow built                  |
| 2026-04-15 | 15/15 tests passing                         |

---

## Next Modules (Phase 2)

- `POST /api/v1/fingerprint/verify` — Fingerprint matching (§3.2)
- `POST /api/v1/risk/grade`         — Risk grading engine (§6.3)
- `POST /api/v1/sanctions/screen`   — UNSCR + IP/PEP screening (§4.2)
- `POST /api/v1/kyc/profile`        — KYC profile builder (§6.1, §6.2)
- `POST /api/v1/lifecycle/review`   — Periodic KYC lifecycle (§5.7)
