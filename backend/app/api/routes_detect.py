"""
Detection API route — POST /api/v1/detect

Accepts a satellite/aerial image and returns pool detection results
with pool type classification.
"""

import logging
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
import cv2

from app.models.detect_pool import PoolDetector
from app.models.classify_pool import PoolClassifier
from app.config import MODEL_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialise models once at module import (shared across requests)
_detector = PoolDetector(model_path=str(MODEL_PATH))
_classifier = PoolClassifier()


@router.post("/detect", summary="Detect and classify swimming pool in an image")
async def detect_pool(file: UploadFile = File(...)) -> JSONResponse:
    """
    Detect swimming pools in an uploaded satellite or aerial image.

    - Runs YOLOv11 segmentation inference.
    - Classifies pool type (in-ground / above-ground / covered / uncovered).
    - Returns bounding box, confidence, pool type, and estimated area in pixels.
    """
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    try:
        raw_bytes = await file.read()
        np_arr = np.frombuffer(raw_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Could not decode image. Check the file format.")

        # ------------------------------------------------------------------
        # Pool detection
        # ------------------------------------------------------------------
        detection = _detector.detect(image)

        # ------------------------------------------------------------------
        # Pool classification (only when a pool is found)
        # ------------------------------------------------------------------
        pool_type = "unknown"
        pool_area = 0.0
        circularity = 0.0
        color_type = "unknown"

        if detection["pool_detected"] and detection.get("mask") is not None:
            mask = np.array(detection["mask"], dtype=np.uint8)
            clf_result = _classifier.classify(image, mask)
            pool_type = clf_result["pool_type"]
            pool_area = clf_result["pool_area"]
            circularity = clf_result.get("circularity", 0.0)
            color_type = clf_result.get("color_type", "unknown")

        return JSONResponse(content={
            "pool_detected": detection["pool_detected"],
            "confidence": detection["confidence"],
            "bbox": detection["bbox"],
            "pool_type": pool_type,
            "pool_area_px": round(pool_area, 1),
            "circularity": circularity,
            "color_type": color_type,
        })

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Detection failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Detection error: {exc}")
