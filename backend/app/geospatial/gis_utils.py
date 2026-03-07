"""
GIS utility functions — coordinate transforms, scale estimation, Haversine distance.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Coordinate transforms
# ---------------------------------------------------------------------------

def pixel_to_latlon(
    px: float,
    py: float,
    image_width: int,
    image_height: int,
    bbox_latlon: tuple,
) -> tuple:
    """
    Convert image pixel coordinates to geographic (lat, lon).

    Args:
        px, py:        Pixel column and row (origin at top-left).
        image_width:   Image width in pixels.
        image_height:  Image height in pixels.
        bbox_latlon:   (min_lon, min_lat, max_lon, max_lat) of the image.

    Returns:
        (latitude, longitude) as floats.
    """
    min_lon, min_lat, max_lon, max_lat = bbox_latlon
    lon = min_lon + (px / image_width) * (max_lon - min_lon)
    lat = max_lat - (py / image_height) * (max_lat - min_lat)
    return float(lat), float(lon)


def latlon_to_pixel(
    lat: float,
    lon: float,
    image_width: int,
    image_height: int,
    bbox_latlon: tuple,
) -> tuple:
    """
    Convert geographic coordinates to image pixel position.

    Args:
        lat, lon:      Geographic coordinates.
        image_width:   Image width in pixels.
        image_height:  Image height in pixels.
        bbox_latlon:   (min_lon, min_lat, max_lon, max_lat).

    Returns:
        (px, py) pixel column and row (integers).
    """
    min_lon, min_lat, max_lon, max_lat = bbox_latlon
    px = int((lon - min_lon) / (max_lon - min_lon) * image_width)
    py = int((max_lat - lat) / (max_lat - min_lat) * image_height)
    return px, py


# ---------------------------------------------------------------------------
# Distance utilities
# ---------------------------------------------------------------------------

def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Haversine great-circle distance between two lat/lon points.

    Returns:
        Distance in metres.
    """
    R = 6_371_000.0  # Earth mean radius in metres
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


# ---------------------------------------------------------------------------
# Scale / resolution helpers
# ---------------------------------------------------------------------------

def estimate_pixels_per_meter(zoom_level: int, lat: float, tile_size: int = 256) -> float:
    """
    Estimate image resolution (pixels per metre) for Web Mercator tile imagery.

    Uses the standard OSM/Google Maps tile resolution formula.

    Args:
        zoom_level: Web Mercator zoom level (0–21).
        lat:        Latitude in decimal degrees (resolution varies by latitude).
        tile_size:  Tile pixel dimension (256 or 512).

    Returns:
        Pixels per metre.
    """
    # Metres per pixel at given zoom and latitude
    meters_per_pixel = (
        np.cos(np.radians(lat)) * 2.0 * np.pi * 6_378_137.0
    ) / (tile_size * (2 ** zoom_level))
    return 1.0 / meters_per_pixel


def gsd_to_pixels_per_meter(gsd_m: float) -> float:
    """
    Convert ground sample distance (metres/pixel) to pixels/metre.

    Args:
        gsd_m: GSD in metres per pixel (e.g. 0.3 for 30 cm/px).

    Returns:
        Pixels per metre.
    """
    if gsd_m <= 0:
        raise ValueError(f"GSD must be positive, got {gsd_m}")
    return 1.0 / gsd_m


def bbox_area_m2(
    bbox: list,
    pixels_per_meter: float,
) -> float:
    """
    Compute the area of a bounding box in square metres.

    Args:
        bbox:             [x1, y1, x2, y2] in pixels.
        pixels_per_meter: Image resolution.

    Returns:
        Area in m².
    """
    x1, y1, x2, y2 = bbox
    width_m = abs(x2 - x1) / pixels_per_meter
    height_m = abs(y2 - y1) / pixels_per_meter
    return width_m * height_m
