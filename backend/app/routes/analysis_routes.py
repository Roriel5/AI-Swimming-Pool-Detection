from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.request_models import TimeSeriesRequest
from app.services.time_series_service import time_series_analysis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/time-series-analysis")
async def run_time_series(req: TimeSeriesRequest):
    """Compare current satellite imagery with historical data to detect pool changes."""
    try:
        result = time_series_analysis(req.lat, req.lng, req.zoom)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Time-series analysis failed")
        raise HTTPException(status_code=500, detail="Time-series analysis failed")
