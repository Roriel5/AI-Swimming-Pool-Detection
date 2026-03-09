from __future__ import annotations

import math


def _meters_per_pixel(lat: float, zoom: int) -> float:
    """Ground resolution in meters per pixel at given latitude and zoom.

    Uses 78271.51696 (not 156543.03392) because Mapbox GL renders
    with 512 px tiles, halving the meters-per-pixel at each zoom level
    compared to the classic 256 px Web Mercator convention.
    """
    return 78271.51696 * math.cos(math.radians(lat)) / (2 ** zoom)


def pixel_bbox_to_geo_polygon(
    bbox: list[float],
    center_lat: float,
    center_lng: float,
    zoom: int,
    image_width: int,
    image_height: int,
) -> list[list[list[float]]]:
    """Convert a pixel-space bounding box to a GeoJSON Polygon coordinate ring.

    Args:
        bbox: [xmin, ymin, xmax, ymax] in pixels.
        center_lat: Latitude of the tile center.
        center_lng: Longitude of the tile center.
        zoom: Map zoom level used to fetch the tile.
        image_width: Tile width in pixels.
        image_height: Tile height in pixels.

    Returns:
        GeoJSON-compatible coordinates: [[[lng, lat], ...]].
    """
    xmin, ymin, xmax, ymax = bbox
    mpp = _meters_per_pixel(center_lat, zoom)

    # Pixel offsets from image center
    cx = image_width / 2
    cy = image_height / 2

    # Meters per degree
    m_per_deg_lat = 111320.0
    m_per_deg_lng = 111320.0 * math.cos(math.radians(center_lat))

    def px_to_geo(px_x: float, px_y: float) -> list[float]:
        dx_m = (px_x - cx) * mpp
        dy_m = (cy - px_y) * mpp  # y-axis flipped
        lng = center_lng + dx_m / m_per_deg_lng
        lat = center_lat + dy_m / m_per_deg_lat
        return [lng, lat]

    # Clockwise ring
    coords = [
        px_to_geo(xmin, ymin),  # top-left
        px_to_geo(xmax, ymin),  # top-right
        px_to_geo(xmax, ymax),  # bottom-right
        px_to_geo(xmin, ymax),  # bottom-left
        px_to_geo(xmin, ymin),  # close ring
    ]

    return [coords]


def detections_to_geojson(
    detections: list[dict],
    center_lat: float,
    center_lng: float,
    zoom: int,
    image_width: int,
    image_height: int,
) -> dict:
    """Convert a list of detections to a GeoJSON FeatureCollection.

    Each detection dict must have 'bbox' and 'confidence' keys.
    """
    features = []
    for det in detections:
        coords = pixel_bbox_to_geo_polygon(
            det["bbox"],
            center_lat,
            center_lng,
            zoom,
            image_width,
            image_height,
        )
        props = {"confidence": round(det["confidence"], 4)}
        if "pool_type" in det:
            props["pool_type"] = det["pool_type"]
        if "type_confidence" in det:
            props["type_confidence"] = det["type_confidence"]

        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Polygon", "coordinates": coords},
            }
        )

    return {"type": "FeatureCollection", "features": features}
