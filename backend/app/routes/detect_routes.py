from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.request_models import CoordinateRequest
from app.services.detection_service import detect_from_coordinates, detect_from_image

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/tiff",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/detect-by-coordinates")
async def detect_by_coordinates(req: CoordinateRequest):
    """Detect swimming pools at the given map coordinates."""
    try:
        result = detect_from_coordinates(req.lat, req.lng, req.zoom)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Coordinate detection failed")
        raise HTTPException(status_code=500, detail="Detection failed")


@router.post("/detect-image")
async def detect_image(file: UploadFile = File(...)):
    """Detect swimming pools in an uploaded satellite image."""
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Use PNG, JPEG, or TIFF.",
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = detect_from_image(contents)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Image detection failed")
        raise HTTPException(status_code=500, detail="Detection failed")
