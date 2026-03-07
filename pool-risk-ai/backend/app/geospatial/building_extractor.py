"""
OpenStreetMap building footprint extractor.

Uses OSMnx to query building polygons within a radius of a given coordinate.
Returns a GeoDataFrame in WGS-84 (EPSG:4326).
"""

import logging
from typing import Optional

import geopandas as gpd

logger = logging.getLogger(__name__)


class BuildingExtractor:
    """
    Fetches building footprints from OpenStreetMap via OSMnx.

    All results are returned as GeoDataFrames in WGS-84 (EPSG:4326).
    """

    def get_buildings(
        self,
        lat: float,
        lon: float,
        dist: float = 200,
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Fetch building polygons within *dist* metres of a lat/lon point.

        Args:
            lat:  Latitude of the search centre.
            lon:  Longitude of the search centre.
            dist: Search radius in metres.

        Returns:
            GeoDataFrame with a 'geometry' column, or None if nothing is found
            or on any error.
        """
        try:
            import osmnx as ox
        except ImportError:
            logger.error("osmnx is not installed. Run: pip install osmnx")
            return None

        try:
            buildings = ox.features_from_point(
                (lat, lon),
                tags={"building": True},
                dist=dist,
            )
        except Exception as exc:
            logger.error("OSMnx query failed for (%.6f, %.6f): %s", lat, lon, exc)
            return None

        if buildings.empty:
            logger.info("No buildings found within %dm of (%.6f, %.6f)", dist, lat, lon)
            return None

        # Keep only Polygon / MultiPolygon footprints
        buildings = buildings[
            buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        ].copy()

        if buildings.empty:
            return None

        # Ensure WGS-84
        if buildings.crs is None or buildings.crs.to_epsg() != 4326:
            buildings = buildings.to_crs(epsg=4326)

        logger.info("Found %d building(s) near (%.6f, %.6f)", len(buildings), lat, lon)
        return buildings[["geometry"]]

    def get_buildings_in_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Fetch buildings within a geographic bounding box.

        Args:
            north, south, east, west: Bounding-box extents in decimal degrees.

        Returns:
            GeoDataFrame or None.
        """
        try:
            import osmnx as ox
        except ImportError:
            logger.error("osmnx is not installed. Run: pip install osmnx")
            return None

        try:
            buildings = ox.features_from_bbox(
                bbox=(north, south, east, west),
                tags={"building": True},
            )
        except Exception as exc:
            logger.error("OSMnx bbox query failed: %s", exc)
            return None

        if buildings.empty:
            return None

        buildings = buildings[
            buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        ].copy()

        if buildings.empty:
            return None

        if buildings.crs is None or buildings.crs.to_epsg() != 4326:
            buildings = buildings.to_crs(epsg=4326)

        return buildings[["geometry"]]
