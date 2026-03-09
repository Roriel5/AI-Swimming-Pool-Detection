from __future__ import annotations

from pydantic import BaseModel


class BBoxDetection(BaseModel):
    """Single detection with pixel-space bounding box."""

    confidence: float
    bbox: list[float]  # [xmin, ymin, xmax, ymax]


class ImageDetectionResponse(BaseModel):
    """Response for uploaded image detection."""

    pools_detected: int
    detections: list[BBoxDetection]
    # Alias for frontend compatibility
    pools: list[BBoxDetection]


class GeoFeature(BaseModel):
    type: str = "Feature"
    properties: dict
    geometry: dict


class GeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection of detected pools."""

    type: str = "FeatureCollection"
    features: list[GeoFeature]
    pools_detected: int
    # Flat list for frontend backward compatibility
    pools: list[BBoxDetection]


class RiskResult(BaseModel):
    score: float
    level: str
    factors: list[str]


class TimeSeriesResponse(BaseModel):
    pool_added: bool
    pools_added: int
    pools_removed: int
    change_detected: bool
    current_count: int
    historical_count: int


class ScanAreaResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoFeature]
    pools_detected: int
    tiles_scanned: int
    risk: RiskResult
