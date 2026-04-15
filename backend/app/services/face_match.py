"""
Face matching service — NID-aware
BFIU Circular No. 29 — Section 3.3

NID photos are typically:
- Grayscale or low-color
- Lower resolution than live selfies
- Different lighting/contrast
- Compressed/printed artifacts

Strategy: normalize both to grayscale, equalize histogram,
use structural + feature matching with NID-aware thresholds.
"""
import numpy as np
import cv2
from app.core.config import settings


def preprocess_face(face_rgb: np.ndarray, size=(160, 160)) -> np.ndarray:
    """
    Normalize face for NID-aware comparison:
    - Resize to fixed size
    - Convert to grayscale
    - CLAHE histogram equalization (handles low-contrast NID photos)
    - Gaussian blur to reduce noise/artifacts
    """
    resized = cv2.resize(face_rgb, size)
    gray    = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
    clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq      = clahe.apply(gray)
    smooth  = cv2.GaussianBlur(eq, (3, 3), 0)
    return smooth


def histogram_similarity(g1: np.ndarray, g2: np.ndarray) -> float:
    """Grayscale histogram correlation after equalization."""
    h1 = cv2.calcHist([g1], [0], None, [128], [0, 256])
    h2 = cv2.calcHist([g2], [0], None, [128], [0, 256])
    cv2.normalize(h1, h1)
    cv2.normalize(h2, h2)
    return float(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL))


def orb_similarity(g1: np.ndarray, g2: np.ndarray) -> float:
    """ORB feature matching — robust to scale/rotation differences."""
    orb  = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(g1, None)
    kp2, des2 = orb.detectAndCompute(g2, None)

    if des1 is None or des2 is None or len(des1) < 5 or len(des2) < 5:
        return 0.0

    bf      = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    # Lowe's ratio test — more robust than crossCheck for NID photos
    good = []
    for m in matches:
        if len(m) == 2 and m[0].distance < 0.75 * m[1].distance:
            good.append(m[0])

    score = min(1.0, len(good) / max(len(kp1), len(kp2), 1) * 4)
    return float(score)


def ssim_similarity(g1: np.ndarray, g2: np.ndarray) -> float:
    """
    Structural Similarity Index (SSIM) — best for
    comparing NID printed photo vs live face.
    """
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    g1f = g1.astype(float)
    g2f = g2.astype(float)

    mu1    = cv2.GaussianBlur(g1f, (11, 11), 1.5)
    mu2    = cv2.GaussianBlur(g2f, (11, 11), 1.5)
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2= mu1 * mu2

    sig1   = cv2.GaussianBlur(g1f ** 2,   (11, 11), 1.5) - mu1_sq
    sig2   = cv2.GaussianBlur(g2f ** 2,   (11, 11), 1.5) - mu2_sq
    sig12  = cv2.GaussianBlur(g1f * g2f,  (11, 11), 1.5) - mu1_mu2

    num    = (2 * mu1_mu2 + C1) * (2 * sig12 + C2)
    den    = (mu1_sq + mu2_sq + C1) * (sig1 + sig2 + C2)
    ssim   = float(np.mean(num / (den + 1e-8)))
    return max(0.0, min(1.0, ssim))


def pixel_similarity(g1: np.ndarray, g2: np.ndarray) -> float:
    """Normalized absolute difference."""
    diff = cv2.absdiff(g1, g2).astype(float)
    return 1.0 - (diff.mean() / 255.0)


def compare_faces(face1_rgb: np.ndarray, face2_rgb: np.ndarray) -> dict:
    """
    NID-aware face comparison pipeline.

    Weights tuned for NID document vs live selfie:
    - SSIM:       35% — best structural measure for doc photos
    - Histogram:  30% — works after CLAHE equalization
    - ORB:        25% — feature points with Lowe's ratio test
    - Pixel:      10% — supporting signal

    Thresholds lowered for NID context (printed photo degradation).
    """
    # Preprocess both faces (grayscale + CLAHE + normalize)
    g1 = preprocess_face(face1_rgb)
    g2 = preprocess_face(face2_rgb)

    hist_score  = histogram_similarity(g1, g2)
    orb_score   = orb_similarity(g1, g2)
    ssim_score  = ssim_similarity(g1, g2)
    pix_score   = pixel_similarity(g1, g2)

    # Weighted final
    final = (
        ssim_score  * 0.35 +
        hist_score  * 0.30 +
        orb_score   * 0.25 +
        pix_score   * 0.10
    )
    final = round(max(0.0, min(1.0, final)) * 100, 2)

    return {
        "ssim_score":      round(ssim_score  * 100, 2),
        "histogram_score": round(hist_score  * 100, 2),
        "feature_score":   round(orb_score   * 100, 2),
        "pixel_score":     round(pix_score   * 100, 2),
        "confidence":      final,
    }


def get_verdict(
    nid_face_found:  bool,
    live_face_found: bool,
    liveness_passed: bool,
    confidence:      float,
) -> tuple:
    if not nid_face_found:
        return "FAILED", "No face detected in NID image"
    if not live_face_found:
        return "FAILED", "No face detected in live capture"
    if not liveness_passed:
        return "FAILED", "Liveness checks failed — retake photo per BFIU Annexure-2"
    if confidence >= settings.MATCH_THRESHOLD:
        return "MATCHED", "Face biometric verified successfully"
    if confidence >= settings.REVIEW_THRESHOLD:
        return "REVIEW",  "Low confidence — manual review recommended"
    return "FAILED", "Face biometric mismatch"
