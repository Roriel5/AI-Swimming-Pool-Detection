from __future__ import annotations

import logging

import cv2
import numpy as np

from app.models.yolo_model import predict
from app.services.tile_fetcher import fetch_satellite_tile
from app.services.geojson_converter import detections_to_geojson, _meters_per_pixel
from app.services.classification_service import classify_detections
from app.services.risk_engine import compute_risk_score

logger = logging.getLogger(__name__)


def _extract_detections(results) -> list[dict]:
    """Extract bounding boxes and confidences from YOLO results."""
    detections: list[dict] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        for i in range(len(boxes)):
            xyxy = boxes.xyxy[i].tolist()
            conf = float(boxes.conf[i])
            detections.append({
                "confidence": round(conf, 4),
                "bbox": [round(v, 2) for v in xyxy],
            })
    return detections


def detect_from_coordinates(
    lat: float, lng: float, zoom: int = 18
) -> dict:
    """Fetch satellite tile at coordinates and run pool detection.

    Returns a dict with GeoJSON features and flat pool list.
    """
    tile = fetch_satellite_tile(lat, lng, zoom)
    h, w = tile.shape[:2]

    results = predict(tile)
    detections = _extract_detections(results)

    # Enrich with pool classification
    classify_detections(tile, detections)

    # Compute risk score
    mpp = _meters_per_pixel(lat, zoom)
    risk = compute_risk_score(detections, mpp)

    geojson = detections_to_geojson(detections, lat, lng, zoom, w, h)

    pools = [
        {"confidence": d["confidence"], "bbox": d["bbox"]}
        for d in detections
    ]

    return {
        **geojson,
        "pools_detected": len(detections),
        "pools": pools,
        "risk": risk,
    }


def detect_from_image(image_bytes: bytes) -> dict:
    """Run pool detection on an uploaded image.

    Returns detection results with pixel-space bounding boxes.
    """
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode uploaded image")

    results = predict(img)
    detections = _extract_detections(results)

    pools = [
        {"confidence": d["confidence"], "bbox": d["bbox"]}
        for d in detections
    ]

    return {
        "pools_detected": len(detections),
        "detections": pools,
        "pools": pools,
    }
