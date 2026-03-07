"""
Insurance risk scoring engine for swimming pools.

Scoring table
-------------
Pool present                        +40
Uncovered or in-ground pool         +25  (above-ground → +10)
Large pool  (> LARGE_POOL_AREA_M2)  +20
Distance < CLOSE_DISTANCE_M         +15  (< 6 m → +8)
No fence                            +20
Newly built pool                    +25

Risk levels
-----------
0 – 50   → LOW
51 – 90  → MEDIUM
91+      → HIGH
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Calculates an insurance risk score from pool analysis inputs.

    All score constants are class attributes so they can be overridden
    without sub-classing.
    """

    # Point values for each risk factor
    SCORE_POOL_PRESENT: int = 40
    SCORE_UNCOVERED: int = 25
    SCORE_ABOVE_GROUND: int = 10
    SCORE_LARGE_POOL: int = 20
    SCORE_VERY_CLOSE: int = 15   # < CLOSE_DISTANCE_M
    SCORE_MODERATELY_CLOSE: int = 8  # < 6 m
    SCORE_NO_FENCE: int = 20
    SCORE_NEW_POOL: int = 25

    # Thresholds
    LARGE_POOL_AREA_M2: float = 50.0   # m² — treated as m² when distance is supplied
    LARGE_POOL_AREA_PX: float = 10_000.0  # pixel² fallback
    CLOSE_DISTANCE_M: float = 3.0
    MODERATE_DISTANCE_M: float = 6.0

    def calculate(self, factors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute the risk score from a pool's analysed attributes.

        Args:
            factors: dict with (all keys optional, missing = conservative default)
                pool_detected       (bool)
                pool_type           (str)   'in-ground' | 'above-ground' | 'covered' | 'uncovered'
                pool_area           (float) m² when distance_from_house is known, else pixels²
                distance_from_house (float | None) metres; None = unknown
                fence_detected      (bool)
                new_pool            (bool)

        Returns:
            dict with:
                risk_score  (int)
                risk_level  (str)  'LOW' | 'MEDIUM' | 'HIGH'
                risk_factors (List[str])  human-readable breakdown
        """
        pool_detected: bool = factors.get("pool_detected", False)

        if not pool_detected:
            return {
                "risk_score": 0,
                "risk_level": "LOW",
                "risk_factors": ["No pool detected — no additional risk."],
            }

        score = 0
        risk_factors: List[str] = []

        pool_type: str = factors.get("pool_type", "unknown")
        pool_area: float = float(factors.get("pool_area", 0.0) or 0.0)
        distance_m: Optional[float] = factors.get("distance_from_house", None)
        fence_detected: bool = bool(factors.get("fence_detected", False))
        new_pool: bool = bool(factors.get("new_pool", False))

        # --- Pool present ------------------------------------------------
        score += self.SCORE_POOL_PRESENT
        risk_factors.append(f"Pool detected (+{self.SCORE_POOL_PRESENT})")

        # --- Pool type ---------------------------------------------------
        if pool_type in ("uncovered", "in-ground"):
            score += self.SCORE_UNCOVERED
            risk_factors.append(
                f"Uncovered / in-ground pool, higher drowning risk (+{self.SCORE_UNCOVERED})"
            )
        elif pool_type == "above-ground":
            score += self.SCORE_ABOVE_GROUND
            risk_factors.append(f"Above-ground pool (+{self.SCORE_ABOVE_GROUND})")
        elif pool_type == "covered":
            risk_factors.append("Covered pool — reduced risk (no additional score)")

        # --- Pool size ---------------------------------------------------
        # Use m² threshold when distance is present (implies a calibrated scale)
        area_threshold = (
            self.LARGE_POOL_AREA_M2 if distance_m is not None else self.LARGE_POOL_AREA_PX
        )
        unit = "m²" if distance_m is not None else "px²"
        if pool_area > area_threshold:
            score += self.SCORE_LARGE_POOL
            risk_factors.append(
                f"Large pool ({pool_area:.0f} {unit} > {area_threshold:.0f} {unit})"
                f" (+{self.SCORE_LARGE_POOL})"
            )

        # --- Distance from house -----------------------------------------
        if distance_m is not None and not (distance_m != distance_m):  # NaN guard
            if distance_m < self.CLOSE_DISTANCE_M:
                score += self.SCORE_VERY_CLOSE
                risk_factors.append(
                    f"Pool very close to building ({distance_m:.1f} m < {self.CLOSE_DISTANCE_M} m)"
                    f" (+{self.SCORE_VERY_CLOSE})"
                )
            elif distance_m < self.MODERATE_DISTANCE_M:
                score += self.SCORE_MODERATELY_CLOSE
                risk_factors.append(
                    f"Pool moderately close to building ({distance_m:.1f} m)"
                    f" (+{self.SCORE_MODERATELY_CLOSE})"
                )
            else:
                risk_factors.append(
                    f"Pool distance from building is adequate ({distance_m:.1f} m, no extra score)"
                )
        else:
            risk_factors.append("Building distance unavailable — not scored")

        # --- Fence -------------------------------------------------------
        if not fence_detected:
            score += self.SCORE_NO_FENCE
            risk_factors.append(f"No fence detected — unsecured pool (+{self.SCORE_NO_FENCE})")
        else:
            risk_factors.append("Fence detected — pool appears secured (no additional score)")

        # --- New pool ----------------------------------------------------
        if new_pool:
            score += self.SCORE_NEW_POOL
            risk_factors.append(
                f"Newly constructed pool (change detected) (+{self.SCORE_NEW_POOL})"
            )

        return {
            "risk_score": score,
            "risk_level": self._score_to_level(score),
            "risk_factors": risk_factors,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_level(score: int) -> str:
        if score <= 50:
            return "LOW"
        if score <= 90:
            return "MEDIUM"
        return "HIGH"
