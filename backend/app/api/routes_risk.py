"""
Risk assessment API route — POST /api/v1/risk

Accepts a current image (and optional prior-date image) and returns a
full insurance risk report:
  - pool detection & classification
  - fence detection
  - distance from nearest building (requires lat/lon)
  - change detection (newly built pool)
  - risk score and level
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
import cv2

from app.models.detect_pool import PoolDetector
from app.models.classify_pool import PoolClassifier, detect_fence
from app.risk_engine.risk_scoring import RiskScorer
from app.change_detection.change_detector import ChangeDetector
from app.config import MODEL_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

# Shared singletons
_detector = PoolDetector(model_path=str(MODEL_PATH))
_classifier = PoolClassifier()
_risk_scorer = RiskScorer()
_change_detector = ChangeDetector(pool_detector=_detector)


def _decode_image(raw: bytes) -> np.ndarray:
    """Decode raw bytes to a BGR numpy array."""
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes.")
    return img


@router.post("/risk", summary="Full insurance risk assessment for a property image")
async def assess_risk(
    file: UploadFile = File(..., description="Current satellite/aerial image"),
    file_t1: Optional[UploadFile] = File(
        None, description="Prior-date image for change detection (optional)"
    ),
    lat: Optional[float] = Form(
        None, description="Latitude for OSM building lookup (optional)"
    ),
    lon: Optional[float] = Form(
        None, description="Longitude for OSM building lookup (optional)"
    ),
    pixels_per_meter: float = Form(
        0.5, description="Image resolution — pixels per metre (default 0.5)"
    ),
) -> JSONResponse:
    """
    Full risk assessment pipeline:

    1. Pool detection (YOLOv11 segmentation)
    2. Pool type classification
    3. Fence detection (edge-based heuristic)
    4. Building distance (OSM via lat/lon, optional)
    5. Change detection (compare against prior image, optional)
    6. Risk scoring (rule-based engine)
    """
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Primary file must be an image.")

    try:
        image = _decode_image(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        # ------------------------------------------------------------------
        # 1. Detection
        # ------------------------------------------------------------------
        detection = _detector.detect(image)
        pool_detected = detection["pool_detected"]
        confidence = detection["confidence"]

        # ------------------------------------------------------------------
        # 2. Classification
        # ------------------------------------------------------------------
        pool_type = "unknown"
        pool_area_px = 0.0
        mask: Optional[np.ndarray] = None

        if pool_detected and detection.get("mask") is not None:
            mask = np.array(detection["mask"], dtype=np.uint8)
            clf = _classifier.classify(image, mask)
            pool_type = clf["pool_type"]
            pool_area_px = clf["pool_area"]

        # ------------------------------------------------------------------
        # 3. Fence detection
        # ------------------------------------------------------------------
        fence_detected = False
        if pool_detected and mask is not None:
            fence_detected = detect_fence(image, mask)

        # ------------------------------------------------------------------
        # 4. Change detection (optional)
        # ------------------------------------------------------------------
        change_detected = False
        if file_t1 is not None:
            try:
                image_t1 = _decode_image(await file_t1.read())
                change_result = _change_detector.detect_change(image_t1, image)
                change_detected = change_result["new_pool"]
            except Exception as cd_exc:
                logger.warning("Change detection skipped: %s", cd_exc)

        # ------------------------------------------------------------------
        # 5. Building distance (optional — needs lat/lon)
        # ------------------------------------------------------------------
        distance_m: Optional[float] = None
        distance_str = "N/A"

        if pool_detected and lat is not None and lon is not None:
            try:
                from app.geospatial.building_extractor import BuildingExtractor
                from app.geospatial.distance_calculator import DistanceCalculator

                buildings = BuildingExtractor().get_buildings(lat, lon, dist=200)
                if buildings is not None and not buildings.empty:
                    calc = DistanceCalculator(pixels_per_meter=pixels_per_meter)
                    bbox = detection.get("bbox", [])
                    if bbox:
                        distance_m = calc.compute_distance_from_bbox(
                            bbox, buildings, image.shape[:2]
                        )
                        distance_str = f"{distance_m:.1f}m"
            except Exception as geo_exc:
                logger.warning("Geospatial analysis skipped: %s", geo_exc)

        # ------------------------------------------------------------------
        # 6. Risk scoring
        # ------------------------------------------------------------------
        risk_input = {
            "pool_detected": pool_detected,
            "pool_type": pool_type,
            "pool_area": pool_area_px,
            "distance_from_house": distance_m,
            "fence_detected": fence_detected,
            "new_pool": change_detected,
        }
        risk = _risk_scorer.calculate(risk_input)

        return JSONResponse(content={
            "pool_detected": pool_detected,
            "pool_type": pool_type,
            "confidence": confidence,
            "distance_from_house": distance_str,
            "fence_detected": fence_detected,
            "change_detected": change_detected,
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "risk_factors": risk["risk_factors"],
        })

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Risk assessment failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Risk assessment error: {exc}")
