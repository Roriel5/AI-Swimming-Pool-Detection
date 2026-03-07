"""
Time-series change detector for swimming pool detection.

Compares two satellite images (different dates) to identify:
  - Newly constructed pools  (pool present in t2 but not t1)
  - Removed pools            (pool present in t1 but not t2)

Primary method: run the YOLO detector on both images and compare detections.
Structural similarity (SSIM) is computed as a secondary signal.
A pixel-difference heuristic is available as a no-model fallback.
"""

import logging
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ChangeDetector:
    """
    Detect newly built or removed swimming pools between two satellite images.

    Args:
        pool_detector: A PoolDetector instance.  When None a colour-based
                       heuristic is used as fallback.
        ssim_threshold: Images with SSIM below this value are flagged as
                        significantly changed (informational only).
    """

    def __init__(
        self,
        pool_detector=None,
        ssim_threshold: float = 0.85,
    ) -> None:
        self.pool_detector = pool_detector
        self.ssim_threshold = ssim_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_change(
        self,
        image_t1: np.ndarray,
        image_t2: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Compare two images to detect pool construction or removal.

        Args:
            image_t1: Earlier (before) image in BGR format.
            image_t2: Later  (after)  image in BGR format.

        Returns:
            dict with:
                new_pool          (bool)  — pool appeared between t1 and t2
                pool_removed      (bool)  — pool disappeared
                pool_detected_t1  (bool)
                pool_detected_t2  (bool)
                ssim_score        (float) — 0..1, higher = more similar
                significant_change(bool)  — ssim < threshold
                diff_map          (List or None) — thresholded difference image
        """
        # Align sizes — resize t1 to match t2
        if image_t1.shape[:2] != image_t2.shape[:2]:
            h2, w2 = image_t2.shape[:2]
            image_t1 = cv2.resize(image_t1, (w2, h2), interpolation=cv2.INTER_LINEAR)

        ssim_score = self._compute_ssim(image_t1, image_t2)

        # Pool detection on both frames
        if self.pool_detector is not None:
            det_t1 = self.pool_detector.detect(image_t1)
            det_t2 = self.pool_detector.detect(image_t2)
            pool_t1 = det_t1.get("pool_detected", False)
            pool_t2 = det_t2.get("pool_detected", False)
        else:
            pool_t1 = self._heuristic_has_pool(image_t1)
            pool_t2 = self._heuristic_has_pool(image_t2)

        diff_map = self._compute_diff_map(image_t1, image_t2)

        return {
            "new_pool": pool_t2 and not pool_t1,
            "pool_removed": pool_t1 and not pool_t2,
            "pool_detected_t1": pool_t1,
            "pool_detected_t2": pool_t2,
            "ssim_score": round(float(ssim_score), 4),
            "significant_change": ssim_score < self.ssim_threshold,
            "diff_map": diff_map.tolist() if diff_map is not None else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Structural similarity index between two images."""
        try:
            from skimage.metrics import structural_similarity as sk_ssim

            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            score, _ = sk_ssim(gray1, gray2, full=True)
            return float(score)
        except ImportError:
            logger.warning("scikit-image not available — using MSE-based similarity fallback.")
            return self._mse_similarity(img1, img2)
        except Exception as exc:
            logger.warning("SSIM computation failed: %s", exc)
            return 1.0

    @staticmethod
    def _mse_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
        """1 − normalised MSE as a simple similarity proxy."""
        diff = img1.astype(np.float32) - img2.astype(np.float32)
        mse = float(np.mean(diff ** 2))
        return max(0.0, 1.0 - mse / (255.0 ** 2))

    @staticmethod
    def _compute_diff_map(
        img1: np.ndarray,
        img2: np.ndarray,
        threshold: int = 30,
    ) -> Optional[np.ndarray]:
        """
        Threshold absolute difference between two greyscale images.

        Returns a binary uint8 array (255 where change exceeds threshold).
        """
        try:
            g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(g1, g2)
            _, diff_bin = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
            return diff_bin
        except Exception as exc:
            logger.debug("Diff map computation failed: %s", exc)
            return None

    @staticmethod
    def _heuristic_has_pool(image: np.ndarray) -> bool:
        """
        Blue-water heuristic: detect pixel clusters in the HSV blue range
        as a proxy for pool presence when no model is available.

        Returns True when > 2 % of image pixels fall in the blue-water range.
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_ratio = mask.sum() / (255.0 * mask.size)
        return bool(blue_ratio > 0.02)
