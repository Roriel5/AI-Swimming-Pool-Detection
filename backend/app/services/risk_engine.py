from __future__ import annotations

import math


def _pool_area_pixels(bbox: list[float]) -> float:
    """Compute bounding box area in pixels."""
    xmin, ymin, xmax, ymax = bbox
    return (xmax - xmin) * (ymax - ymin)


def _pool_area_sqm(bbox: list[float], mpp: float) -> float:
    """Compute approximate pool area in square meters."""
    return _pool_area_pixels(bbox) * (mpp ** 2)


def compute_risk_score(detections: list[dict], mpp: float = 0.25) -> dict:
    """Compute a risk score (0--100) for a set of pool detections.

    Args:
        detections: List of dicts, each with 'confidence', 'bbox',
                    'pool_type' (optional).
        mpp: Meters per pixel for area estimation.

    Returns:
        {"risk_score": int, "risk_level": str, "risk_factors": list[str]}
    """
    if not detections:
        return {"risk_score": 0, "risk_level": "Low", "risk_factors": []}

    base = 40
    factors: list[str] = []

    # --- Pool type risks ---
    pool_types = [d.get("pool_type", "in_ground") for d in detections]

    if "uncovered" in pool_types:
        base += 15
        factors.append("Uncovered pool present")

    if "above_ground" in pool_types:
        base += 10
        factors.append("Above-ground pool detected")

    # --- Size risk ---
    LARGE_POOL_SQM = 50.0  # ~7m x 7m
    areas = [_pool_area_sqm(d["bbox"], mpp) for d in detections]
    max_area = max(areas) if areas else 0

    if max_area > LARGE_POOL_SQM:
        base += 10
        factors.append(f"Large pool ({max_area:.0f} sqm)")

    # --- Multiple pools ---
    if len(detections) >= 2:
        base += 10
        factors.append(f"Multiple pools ({len(detections)})")

    # --- Low confidence penalty (model uncertainty) ---
    avg_conf = sum(d["confidence"] for d in detections) / len(detections)
    if avg_conf < 0.6:
        base += 5
        factors.append("Low detection confidence")

    score = max(0, min(100, base))

    if score <= 30:
        level = "Low"
    elif score <= 60:
        level = "Medium"
    else:
        level = "High"

    return {
        "risk_score": score,
        "risk_level": level,
        "risk_factors": factors,
    }
