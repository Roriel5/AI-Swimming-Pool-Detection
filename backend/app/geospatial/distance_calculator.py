"""
Geometric distance calculator between pool and building polygons.

Operates in pixel space (image coordinates).  Call pixels_to_meters() to
convert once you know the ground sample distance or zoom level of the imagery.
"""

import logging
from typing import List, Optional, Tuple

import cv2
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, box

logger = logging.getLogger(__name__)


class DistanceCalculator:
    """
    Computes minimum Shapely distances between a pool polygon and
    OSM building footprints, then converts to metres.

    NOTE: building footprints from OSMnx are in geographic CRS (lat/lon).
    When working purely in pixel space, you must supply building polygons
    that have been reprojected to pixel coordinates.  For the
    common case where pixel-to-metre scale is known, pass the bounding-box
    parameters to reproject, or use raw pixel distances with pixels_per_meter.
    """

    def __init__(self, pixels_per_meter: float = 0.5) -> None:
        """
        Args:
            pixels_per_meter: Image resolution.
                              E.g. 0.5 means 1 pixel = 2 metres.
                              Typical values: 0.1 (very high-res) to 1.0 (medium-res).
        """
        self.pixels_per_meter = pixels_per_meter

    # ------------------------------------------------------------------
    # Unit conversion
    # ------------------------------------------------------------------

    def pixels_to_meters(self, pixels: float) -> float:
        """Convert a pixel-space distance to metres."""
        return pixels / self.pixels_per_meter

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def bbox_to_polygon(self, bbox: List[int]) -> Polygon:
        """Convert [x1, y1, x2, y2] bounding box to a Shapely Polygon."""
        x1, y1, x2, y2 = bbox
        return box(x1, y1, x2, y2)

    def mask_to_polygon(self, mask: np.ndarray) -> Optional[Polygon]:
        """
        Extract the largest contour from a binary mask and return it as a
        Shapely Polygon in image pixel coordinates.

        Args:
            mask: binary array (0/1 or 0/255).

        Returns:
            Shapely Polygon, or None if the mask is empty.
        """
        mask_u8 = (mask > 0).astype(np.uint8) * 255
        contours, _ = cv2.findContours(
            mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None

        contour = max(contours, key=cv2.contourArea)
        if len(contour) < 3:
            return None

        pts = [(int(p[0][0]), int(p[0][1])) for p in contour]
        try:
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
            return poly
        except Exception as exc:
            logger.warning("Could not build polygon from mask contour: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public distance API
    # ------------------------------------------------------------------

    def compute_distance_from_bbox(
        self,
        pool_bbox: List[int],
        buildings_gdf: gpd.GeoDataFrame,
        image_shape: Tuple[int, int],
    ) -> float:
        """
        Minimum pixel-space distance from pool bounding box to nearest building,
        converted to metres.

        Args:
            pool_bbox:     [x1, y1, x2, y2] in pixels.
            buildings_gdf: GeoDataFrame whose geometries are in pixel coordinates.
            image_shape:   (height, width) — unused here but kept for API symmetry.

        Returns:
            Distance in metres.  Returns float('inf') when no buildings exist.
        """
        pool_poly = self.bbox_to_polygon(pool_bbox)
        dist_px = self._min_distance_px(pool_poly, buildings_gdf)
        return self.pixels_to_meters(dist_px)

    def compute_distance_from_mask(
        self,
        pool_mask: np.ndarray,
        buildings_gdf: gpd.GeoDataFrame,
    ) -> float:
        """
        Minimum pixel-space distance from pool mask contour to nearest building,
        converted to metres.

        Args:
            pool_mask:     Binary mask array.
            buildings_gdf: GeoDataFrame whose geometries are in pixel coordinates.

        Returns:
            Distance in metres.
        """
        pool_poly = self.mask_to_polygon(pool_mask)
        if pool_poly is None:
            logger.warning("Could not extract pool polygon — returning inf distance.")
            return float("inf")
        dist_px = self._min_distance_px(pool_poly, buildings_gdf)
        return self.pixels_to_meters(dist_px)

    def compute_pool_area_m2(self, pool_mask: np.ndarray) -> float:
        """
        Estimate pool surface area in square metres from a binary mask.

        Args:
            pool_mask: binary array.

        Returns:
            Area in m².
        """
        area_px = float(np.sum(pool_mask > 0))
        return area_px / (self.pixels_per_meter ** 2)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _min_distance_px(
        self,
        pool_poly: Polygon,
        buildings_gdf: gpd.GeoDataFrame,
    ) -> float:
        """Return minimum Shapely distance (pixels) to the nearest building."""
        min_dist = float("inf")
        for geom in buildings_gdf.geometry:
            try:
                d = pool_poly.distance(geom)
                if d < min_dist:
                    min_dist = d
            except Exception as exc:
                logger.debug("Skipping geometry during distance calc: %s", exc)
        return min_dist
