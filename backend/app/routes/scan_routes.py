from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.request_models import ScanAreaRequest
from app.services.scan_service import scan_area

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/scan-area")
async def run_scan_area(req: ScanAreaRequest):
    """Scan a geographic bounding box for swimming pools."""
    try:
        result = scan_area(
            north=req.north,
            south=req.south,
            east=req.east,
            west=req.west,
            zoom=req.zoom,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Area scan failed")
        raise HTTPException(status_code=500, detail="Area scan failed")
