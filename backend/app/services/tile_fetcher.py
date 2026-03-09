from __future__ import annotations

import logging

import cv2
import numpy as np
import requests

from app.config import MAPBOX_ACCESS_TOKEN, MAPBOX_TILE_URL, TILE_SIZE

logger = logging.getLogger(__name__)

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    """Reuse a single requests session for connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def fetch_satellite_tile(
    lat: float,
    lng: float,
    zoom: int = 18,
    size: int = TILE_SIZE,
    token: str | None = None,
) -> np.ndarray:
    """Download a Mapbox satellite tile and return it as a BGR numpy array.

    Raises:
        ValueError: If Mapbox returns a non-image response.
        requests.HTTPError: On HTTP errors.
    """
    token = token or MAPBOX_ACCESS_TOKEN
    url = MAPBOX_TILE_URL.format(
        lng=lng, lat=lat, zoom=zoom, size=size, token=token
    )

    logger.debug("Fetching tile: lat=%.6f lng=%.6f zoom=%d", lat, lng, zoom)
    resp = _get_session().get(url, timeout=15)
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "image" not in content_type:
        raise ValueError(f"Expected image, got {content_type}: {resp.text[:200]}")

    img_array = np.frombuffer(resp.content, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode satellite tile image")

    logger.debug("Tile fetched: %dx%d", img.shape[1], img.shape[0])
    return img
