from __future__ import annotations

import logging
import math

import numpy as np

from app.models.yolo_model import predict
from app.services.tile_fetcher import fetch_satellite_tile

logger = logging.getLogger(__name__)


def _extract_centers(results) -> list[tuple[float, float]]:
    """Extract bounding-box centers from YOLO results."""
    centers: list[tuple[float, float]] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        for i in range(len(boxes)):
            xyxy = boxes.xyxy[i].tolist()
            cx = (xyxy[0] + xyxy[2]) / 2
            cy = (xyxy[1] + xyxy[3]) / 2
            centers.append((cx, cy))
    return centers


def _count_detections(results) -> int:
    count = 0
    for r in results:
        if r.boxes is not None:
            count += len(r.boxes)
    return count


def _match_pools(
    prev_centers: list[tuple[float, float]],
    curr_centers: list[tuple[float, float]],
    threshold_px: float = 60.0,
) -> dict:
    """Match previous and current detections by proximity.

    Returns dict with matched, added, removed counts and details.
    """
    matched_prev = set()
    matched_curr = set()

    for ci, (cx, cy) in enumerate(curr_centers):
        best_dist = float("inf")
        best_pi = -1
        for pi, (px, py) in enumerate(prev_centers):
            if pi in matched_prev:
                continue
            dist = math.hypot(cx - px, cy - py)
            if dist < best_dist:
                best_dist = dist
                best_pi = pi
        if best_dist < threshold_px and best_pi >= 0:
            matched_prev.add(best_pi)
            matched_curr.add(ci)

    added = [i for i in range(len(curr_centers)) if i not in matched_curr]
    removed = [i for i in range(len(prev_centers)) if i not in matched_prev]

    return {
        "matched": len(matched_curr),
        "added_indices": added,
        "removed_indices": removed,
    }


def time_series_analysis(
    lat: float,
    lng: float,
    zoom: int = 18,
) -> dict:
    """Compare current vs historical satellite imagery for change detection.

    Since Mapbox Static API doesn't directly support historical dates,
    we simulate by fetching the same tile twice (current state) and
    comparing against a slightly offset tile to demonstrate the pipeline.
    In production this would use a temporal imagery provider.
    """
    logger.info("Time-series analysis at lat=%.6f lng=%.6f", lat, lng)

    # Current tile
    current_tile = fetch_satellite_tile(lat, lng, zoom)
    current_results = predict(current_tile)
    current_count = _count_detections(current_results)
    current_centers = _extract_centers(current_results)

    # Historical tile — small spatial offset to simulate temporal difference
    # In production: fetch from a historical imagery API with a date param
    offset_deg = 0.0008  # ~90m shift
    hist_tile = fetch_satellite_tile(lat + offset_deg, lng + offset_deg, zoom)
    hist_results = predict(hist_tile)
    hist_count = _count_detections(hist_results)
    hist_centers = _extract_centers(hist_results)

    match_result = _match_pools(hist_centers, current_centers)

    pools_added = len(match_result["added_indices"])
    pools_removed = len(match_result["removed_indices"])

    return {
        "previous_pool_count": hist_count,
        "current_pool_count": current_count,
        "pools_added": pools_added,
        "pools_removed": pools_removed,
        "pool_added": pools_added > 0,
        "pool_removed": pools_removed > 0,
        "change_detected": pools_added > 0 or pools_removed > 0,
        "analysis": {
            "matched_pools": match_result["matched"],
            "new_pool_indices": match_result["added_indices"],
            "removed_pool_indices": match_result["removed_indices"],
        },
    }
