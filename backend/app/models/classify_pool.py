"""
Pool type classification and fence detection using OpenCV shape/colour analysis.

Classification logic
--------------------
Shape analysis (contour):
    - circularity > 0.70  → above-ground  (round pools are typically above-ground)
    - high aspect ratio   → rectangular   (likely in-ground)

Colour analysis (HSV):
    - blue hue  (100–130) dominant → uncovered (water visible)
    - green tarp (35–85)  dominant → covered
    - low saturation grey           → covered

Final pool_type decision:
    covered       ← grey surface or tarp
    above-ground  ← circular shape
    in-ground     ← rectangular + blue water
    uncovered     ← any shape + blue water (fallback)
"""

import logging
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Standalone fence detection helper (also imported by routes_risk)
# ---------------------------------------------------------------------------

def detect_fence(
    image: np.ndarray,
    pool_mask: np.ndarray,
    margin: int = 50,
) -> bool:
    """
    Heuristic fence detector using Canny edge analysis in the region
    surrounding the pool.

    Args:
        image:      BGR image.
        pool_mask:  Binary pool mask (0/1 or 0/255).
        margin:     Pixel ring width around pool bounding box to search.

    Returns:
        True if a fence-like enclosure is detected.
    """
    h, w = image.shape[:2]
    mask_u8 = (pool_mask > 0).astype(np.uint8) * 255

    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False

    pool_cnt = max(contours, key=cv2.contourArea)
    x, y, pw, ph = cv2.boundingRect(pool_cnt)

    # Expanded region-of-interest
    x1, y1 = max(0, x - margin), max(0, y - margin)
    x2, y2 = min(w, x + pw + margin), min(h, y + ph + margin)
    roi = image[y1:y2, x1:x2]

    if roi.size == 0:
        return False

    # Edge map in ROI
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # Mask out the pool region itself — we only care about the surrounding ring
    roi_h, roi_w = roi.shape[:2]
    pool_in_roi = mask_u8[y1:y2, x1:x2]
    ring_mask = np.ones((roi_h, roi_w), dtype=np.uint8) * 255
    ring_mask[pool_in_roi > 0] = 0
    edges_ring = cv2.bitwise_and(edges, ring_mask)

    # Look for large rectangular-ish contours (fence posts / enclosure line)
    enc_contours, _ = cv2.findContours(edges_ring, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pool_area = cv2.contourArea(pool_cnt)

    for cnt in enc_contours:
        area = cv2.contourArea(cnt)
        if area < 800:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) in (4, 5, 6) and area > pool_area * 0.7:
            return True

    # Fallback: high edge density in surrounding ring ↔ fence-like structures
    edge_density = edges_ring.sum() / max(ring_mask.sum(), 1)
    return bool(edge_density > 0.08 * 255)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class PoolClassifier:
    """
    Classifies a segmented pool as:
      in-ground | above-ground | covered | uncovered

    Uses contour shape analysis and HSV colour analysis on the pool mask region.
    """

    # HSV ranges
    _BLUE_LOWER = np.array([90, 50, 50])
    _BLUE_UPPER = np.array([130, 255, 255])
    _TARP_LOWER = np.array([35, 30, 30])
    _TARP_UPPER = np.array([85, 255, 255])
    _GREY_LOWER = np.array([0, 0, 80])
    _GREY_UPPER = np.array([180, 40, 200])

    CIRCULARITY_THRESHOLD: float = 0.70
    BLUE_RATIO_THRESHOLD: float = 0.25
    TARP_RATIO_THRESHOLD: float = 0.20
    GREY_RATIO_THRESHOLD: float = 0.30

    def classify(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
        """
        Classify pool type from an image and its binary segmentation mask.

        Args:
            image: BGR uint8 array.
            mask:  Binary mask array (0/1 values).

        Returns:
            dict with:
                pool_type   (str)
                pool_area   (float)  — area in pixels²
                shape_type  (str)
                color_type  (str)
                circularity (float)
        """
        mask_u8 = (mask > 0).astype(np.uint8) * 255

        shape_type, area_px, circularity = self._analyse_shape(mask_u8)
        color_type = self._analyse_color(image, mask_u8)
        pool_type = self._decide_type(shape_type, color_type)

        return {
            "pool_type": pool_type,
            "pool_area": float(area_px),
            "shape_type": shape_type,
            "color_type": color_type,
            "circularity": round(float(circularity), 4),
        }

    # ------------------------------------------------------------------
    # Shape analysis
    # ------------------------------------------------------------------

    def _analyse_shape(
        self, mask_u8: np.ndarray
    ) -> Tuple[str, float, float]:
        """
        Returns (shape_type, area_pixels, circularity).
        shape_type ∈ {'circular', 'rectangular', 'irregular', 'unknown'}
        """
        contours, _ = cv2.findContours(
            mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return "unknown", 0.0, 0.0

        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        if perimeter < 1e-3:
            return "unknown", float(area), 0.0

        # Isoperimetric quotient (1.0 = perfect circle)
        circularity = 4.0 * np.pi * area / (perimeter ** 2)

        x, y, bw, bh = cv2.boundingRect(contour)
        aspect = min(bw, bh) / max(bw, bh) if max(bw, bh) > 0 else 0.0

        if circularity >= self.CIRCULARITY_THRESHOLD:
            return "circular", float(area), float(circularity)
        if aspect >= 0.70:
            return "rectangular", float(area), float(circularity)
        return "irregular", float(area), float(circularity)

    # ------------------------------------------------------------------
    # Colour analysis
    # ------------------------------------------------------------------

    def _analyse_color(self, image: np.ndarray, mask_u8: np.ndarray) -> str:
        """
        Returns color_type ∈ {'blue_water', 'tarp_covered', 'grey_surface', 'unknown'}.
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        total_mask_px = float(mask_u8.sum()) / 255.0 + 1e-6

        def masked_ratio(lower: np.ndarray, upper: np.ndarray) -> float:
            color_mask = cv2.inRange(hsv, lower, upper)
            combined = cv2.bitwise_and(color_mask, mask_u8)
            return float(combined.sum()) / 255.0 / total_mask_px

        if masked_ratio(self._BLUE_LOWER, self._BLUE_UPPER) >= self.BLUE_RATIO_THRESHOLD:
            return "blue_water"
        if masked_ratio(self._TARP_LOWER, self._TARP_UPPER) >= self.TARP_RATIO_THRESHOLD:
            return "tarp_covered"
        if masked_ratio(self._GREY_LOWER, self._GREY_UPPER) >= self.GREY_RATIO_THRESHOLD:
            return "grey_surface"
        return "unknown"

    # ------------------------------------------------------------------
    # Decision logic
    # ------------------------------------------------------------------

    def _decide_type(self, shape_type: str, color_type: str) -> str:
        """Rule-based pool type decision."""
        # Covered first — regardless of shape
        if color_type in ("tarp_covered", "grey_surface"):
            return "covered"

        # Circular → above-ground
        if shape_type == "circular":
            return "above-ground"

        # Rectangular + blue water → classic in-ground
        if shape_type == "rectangular" and color_type == "blue_water":
            return "in-ground"

        # Any shape + blue water → uncovered
        if color_type == "blue_water":
            return "uncovered"

        # Default — most pools are in-ground
        return "in-ground"
