"use client";

import { useRef, useEffect, useState, forwardRef, useImperativeHandle } from "react";
import mapboxgl from "mapbox-gl";
import MapboxGeocoder from "@mapbox/mapbox-gl-geocoder";
import type { MapStyle, Detection, GeoFeature } from "@/types";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;

const MAP_STYLES: Record<MapStyle, string> = {
  satellite: "mapbox://styles/mapbox/satellite-v9",
  streets: "mapbox://styles/mapbox/light-v11",
};

const POOL_COLORS: Record<string, string> = {
  in_ground: "#22d3ee",
  above_ground: "#f59e0b",
  covered: "#8b5cf6",
  uncovered: "#22d3ee",
};

const POOL_OUTLINE_COLORS: Record<string, string> = {
  in_ground: "#06b6d4",
  above_ground: "#d97706",
  covered: "#7c3aed",
  uncovered: "#06b6d4",
};

interface MapViewProps {
  mapStyle: MapStyle;
  onMapClick: (lat: number, lng: number) => void;
  detections: Detection[];
  geoFeatures: GeoFeature[];
  clickCoords: { lat: number; lng: number } | null;
  onBoundsChange?: (bounds: { north: number; south: number; east: number; west: number }) => void;
}

export interface MapViewHandle {
  flyTo: (lng: number, lat: number, zoom?: number) => void;
  getBounds: () => { north: number; south: number; east: number; west: number } | null;
}

const MapView = forwardRef<MapViewHandle, MapViewProps>(
  ({ mapStyle, onMapClick, detections, geoFeatures, clickCoords, onBoundsChange }, ref) => {
    const mapContainer = useRef<HTMLDivElement>(null);
    const map = useRef<mapboxgl.Map | null>(null);
    const marker = useRef<mapboxgl.Marker | null>(null);
    const popup = useRef<mapboxgl.Popup | null>(null);
    const [loaded, setLoaded] = useState(false);
    const prevStyleRef = useRef<MapStyle>(mapStyle);
    const geoFeaturesRef = useRef<GeoFeature[]>(geoFeatures);

    useEffect(() => {
      geoFeaturesRef.current = geoFeatures;
    }, [geoFeatures]);

    useImperativeHandle(ref, () => ({
      flyTo: (lng: number, lat: number, zoom = 17) => {
        map.current?.flyTo({ center: [lng, lat], zoom, duration: 1500 });
      },
      getBounds: () => {
        if (!map.current) return null;
        const b = map.current.getBounds();
        if (!b) return null;
        return {
          north: b.getNorth(),
          south: b.getSouth(),
          east: b.getEast(),
          west: b.getWest(),
        };
      },
    }));

    function addDetectionLayers(m: mapboxgl.Map) {
      if (m.getSource("detections")) return;
      m.addSource("detections", {
        type: "geojson",
        data: { type: "FeatureCollection", features: geoFeaturesRef.current },
      });

      // Pool-type aware fill color
      m.addLayer({
        id: "detection-fill",
        type: "fill",
        source: "detections",
        paint: {
          "fill-color": [
            "match",
            ["coalesce", ["get", "pool_type"], "in_ground"],
            "in_ground", POOL_COLORS.in_ground,
            "above_ground", POOL_COLORS.above_ground,
            "covered", POOL_COLORS.covered,
            "uncovered", POOL_COLORS.uncovered,
            POOL_COLORS.in_ground,
          ],
          "fill-opacity": 0.35,
        },
      });

      m.addLayer({
        id: "detection-outline",
        type: "line",
        source: "detections",
        paint: {
          "line-color": [
            "match",
            ["coalesce", ["get", "pool_type"], "in_ground"],
            "in_ground", POOL_OUTLINE_COLORS.in_ground,
            "above_ground", POOL_OUTLINE_COLORS.above_ground,
            "covered", POOL_OUTLINE_COLORS.covered,
            "uncovered", POOL_OUTLINE_COLORS.uncovered,
            POOL_OUTLINE_COLORS.in_ground,
          ],
          "line-width": 2.5,
          "line-opacity": 1,
        },
      });

      // Popup on click
      m.on("click", "detection-fill", (e) => {
        if (!e.features || e.features.length === 0) return;
        e.originalEvent.stopPropagation();

        const props = e.features[0].properties || {};
        const conf = props.confidence != null ? (props.confidence * 100).toFixed(1) : "–";
        const poolType = (props.pool_type || "unknown").replace(/_/g, " ");
        const typConf =
          props.type_confidence != null
            ? (props.type_confidence * 100).toFixed(0)
            : "–";

        if (popup.current) popup.current.remove();
        popup.current = new mapboxgl.Popup({ closeButton: true, maxWidth: "220px" })
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font-family:Inter,system-ui,sans-serif;font-size:12px;line-height:1.6">
              <div style="font-weight:600;margin-bottom:4px;text-transform:capitalize">${poolType}</div>
              <div style="color:#6b7280">Confidence: <strong style="color:#1a1d23">${conf}%</strong></div>
              <div style="color:#6b7280">Type conf: <strong style="color:#1a1d23">${typConf}%</strong></div>
            </div>`
          )
          .addTo(m);
      });

      m.on("mouseenter", "detection-fill", () => {
        m.getCanvas().style.cursor = "pointer";
      });
      m.on("mouseleave", "detection-fill", () => {
        m.getCanvas().style.cursor = "";
      });
    }

    // Initialize map
    useEffect(() => {
      if (!mapContainer.current) return;

      mapboxgl.accessToken = MAPBOX_TOKEN;

      const m = new mapboxgl.Map({
        container: mapContainer.current,
        style: MAP_STYLES[mapStyle],
        center: [-98.5795, 39.8283],
        zoom: 4,
        attributionControl: false,
      });

      m.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-right");
      m.addControl(new mapboxgl.AttributionControl({ compact: true }), "bottom-right");

      const geocoder = new MapboxGeocoder({
        accessToken: MAPBOX_TOKEN,
        mapboxgl: mapboxgl as any,
        marker: false,
        placeholder: "Search address, city, or ZIP...",
        collapsed: false,
      });
      m.addControl(geocoder, "top-left");

      geocoder.on("result", (e: any) => {
        const [lng, lat] = e.result.center;
        if (marker.current) marker.current.remove();
        marker.current = new mapboxgl.Marker({ color: "#3b6fa0" })
          .setLngLat([lng, lat])
          .addTo(m);
      });

      m.on("load", () => {
        addDetectionLayers(m);
        setLoaded(true);
      });

      m.on("click", (e) => {
        onMapClick(e.lngLat.lat, e.lngLat.lng);
      });

      // Expose viewport bounds on move
      const emitBounds = () => {
        if (!onBoundsChange) return;
        const b = m.getBounds();
        if (!b) return;
        onBoundsChange({
          north: b.getNorth(),
          south: b.getSouth(),
          east: b.getEast(),
          west: b.getWest(),
        });
      };
      m.on("moveend", emitBounds);
      m.on("load", emitBounds);

      map.current = m;

      return () => {
        m.remove();
        map.current = null;
        setLoaded(false);
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Update style
    useEffect(() => {
      if (!map.current || !loaded) return;
      if (prevStyleRef.current === mapStyle) return;
      prevStyleRef.current = mapStyle;

      map.current.setStyle(MAP_STYLES[mapStyle]);
      map.current.once("style.load", () => {
        const m = map.current!;
        addDetectionLayers(m);
      });
    }, [mapStyle, loaded]);

    // Update click marker
    useEffect(() => {
      if (!map.current || !clickCoords) return;
      if (marker.current) marker.current.remove();
      marker.current = new mapboxgl.Marker({ color: "#3b6fa0" })
        .setLngLat([clickCoords.lng, clickCoords.lat])
        .addTo(map.current);
    }, [clickCoords]);

    // Update detections
    useEffect(() => {
      if (!map.current || !loaded) return;
      const m = map.current;

      const applyFeatures = () => {
        const src = m.getSource("detections") as mapboxgl.GeoJSONSource | undefined;
        if (!src) return false;
        src.setData({ type: "FeatureCollection", features: geoFeatures });
        return true;
      };

      if (!applyFeatures()) {
        m.once("style.load", () => applyFeatures());
      }
    }, [geoFeatures, loaded]);

    return <div ref={mapContainer} className="w-full h-full" />;
  }
);

MapView.displayName = "MapView";
export default MapView;
