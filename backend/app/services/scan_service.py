from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.yolo_model import predict
from app.services.tile_fetcher import fetch_satellite_tile
from app.services.geojson_converter import (
    detections_to_geojson,
    _meters_per_pixel,
)
from app.services.classification_service import classify_detections
from app.services.risk_engine import compute_risk_score
from app.config import TILE_SIZE

logger = logging.getLogger(__name__)

# Limit concurrency to avoid overwhelming Mapbox / GPU
MAX_TILES = 64
MAX_WORKERS = 6


def _generate_tile_centers(
    north: float, south: float, east: float, west: float, zoom: int
) -> list[tuple[float, float]]:
    """Generate a grid of tile center coordinates covering the bounding box.

    Tile spacing is based on the ground coverage of a 640px tile at the
    given zoom level.
    """
    mid_lat = (north + south) / 2
    mpp = _meters_per_pixel(mid_lat, zoom)
    tile_span_m = TILE_SIZE * mpp

    m_per_deg_lat = 111320.0
    m_per_deg_lng = 111320.0 * math.cos(math.radians(mid_lat))

    step_lat = tile_span_m / m_per_deg_lat
    step_lng = tile_span_m / m_per_deg_lng

    # Slight overlap (10%) to avoid missing pools on tile edges
    step_lat *= 0.9
    step_lng *= 0.9

    centers: list[tuple[float, float]] = []
    lat = south + step_lat / 2
    while lat <= north:
        lng = west + step_lng / 2
        while lng <= east:
            centers.append((lat, lng))
            lng += step_lng
        lat += step_lat

    return centers


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


def _process_tile(lat: float, lng: float, zoom: int) -> list[dict]:
    """Fetch a single tile, run detection + classification, convert to geo features."""
    try:
        tile = fetch_satellite_tile(lat, lng, zoom)
        h, w = tile.shape[:2]
        results = predict(tile)
        detections = _extract_detections(results)

        if not detections:
            return []

        # Classify each detection
        classify_detections(tile, detections)

        # Compute mpp for risk engine
        mpp = _meters_per_pixel(lat, zoom)

        # Convert to geo features with enriched properties
        features = []
        for det in detections:
            from app.services.geojson_converter import pixel_bbox_to_geo_polygon

            coords = pixel_bbox_to_geo_polygon(
                det["bbox"], lat, lng, zoom, w, h
            )
            features.append({
                "type": "Feature",
                "properties": {
                    "confidence": det["confidence"],
                    "pool_type": det.get("pool_type", "in_ground"),
                    "type_confidence": det.get("type_confidence", 0.5),
                    "tile_center": {"lat": lat, "lng": lng},
                },
                "geometry": {"type": "Polygon", "coordinates": coords},
            })

        return features

    except Exception:
        logger.warning("Failed to process tile at %.6f, %.6f", lat, lng, exc_info=True)
        return []


def scan_area(
    north: float,
    south: float,
    east: float,
    west: float,
    zoom: int = 18,
) -> dict:
    """Scan a geographic bounding box for pools.

    Generates a tile grid, runs detection on each tile in parallel,
    and merges results into a single GeoJSON FeatureCollection.
    """
    if north <= south:
        raise ValueError("north must be greater than south")
    if east <= west:
        raise ValueError("east must be greater than west")

    centers = _generate_tile_centers(north, south, east, west, zoom)

    if len(centers) > MAX_TILES:
        raise ValueError(
            f"Scan area too large: {len(centers)} tiles needed, max is {MAX_TILES}. "
            "Zoom in or reduce the bounding box."
        )

    logger.info("Scanning %d tiles at zoom=%d", len(centers), zoom)

    all_features: list[dict] = []

    # Use ThreadPoolExecutor — tile fetching is I/O-bound, YOLO inference
    # is serialized by the GIL / GPU lock, but we overlap I/O with compute.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_process_tile, lat, lng, zoom): (lat, lng)
            for lat, lng in centers
        }
        for future in as_completed(futures):
            features = future.result()
            all_features.extend(features)

    # Deduplicate detections that overlap at tile borders
    all_features = _deduplicate_features(all_features)

    # Compute aggregate risk
    det_dicts = [
        {
            "confidence": f["properties"]["confidence"],
            "bbox": [0, 0, 10, 10],  # placeholder; risk uses pool_type & count
            "pool_type": f["properties"].get("pool_type", "in_ground"),
        }
        for f in all_features
    ]
    mid_lat = (north + south) / 2
    mpp = _meters_per_pixel(mid_lat, zoom)
    risk = compute_risk_score(det_dicts, mpp)

    return {
        "type": "FeatureCollection",
        "features": all_features,
        "pools_detected": len(all_features),
        "tiles_scanned": len(centers),
        "risk": risk,
    }


def _deduplicate_features(
    features: list[dict], threshold_deg: float = 0.00005
) -> list[dict]:
    """Remove near-duplicate features (from overlapping tile borders).

    Uses centroid distance in degrees; ~5.5m threshold at equator.
    """
    if len(features) <= 1:
        return features

    def _centroid(f: dict) -> tuple[float, float]:
        coords = f["geometry"]["coordinates"][0]
        lngs = [c[0] for c in coords[:-1]]
        lats = [c[1] for c in coords[:-1]]
        return (sum(lngs) / len(lngs), sum(lats) / len(lats))

    centroids = [_centroid(f) for f in features]
    keep = []
    removed = set()

    for i in range(len(features)):
        if i in removed:
            continue
        keep.append(features[i])
        for j in range(i + 1, len(features)):
            if j in removed:
                continue
            dlng = abs(centroids[i][0] - centroids[j][0])
            dlat = abs(centroids[i][1] - centroids[j][1])
            if dlng < threshold_deg and dlat < threshold_deg:
                removed.add(j)

    return keep
