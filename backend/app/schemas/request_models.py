from pydantic import BaseModel, Field


class CoordinateRequest(BaseModel):
    """Request to detect pools at a geographic coordinate."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    zoom: int = Field(default=18, ge=1, le=22, description="Map zoom level")


class TimeSeriesRequest(BaseModel):
    """Request for time-series change detection."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    zoom: int = Field(default=18, ge=1, le=22)


class ScanAreaRequest(BaseModel):
    """Request to scan a bounding box for pools."""

    north: float = Field(..., ge=-90, le=90)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    west: float = Field(..., ge=-180, le=180)
    zoom: int = Field(default=18, ge=1, le=22)
