"use client";

import { useRef, useCallback, useState } from "react";
import dynamic from "next/dynamic";
import TopNav from "@/components/TopNav";
import LeftSidebar from "@/components/LeftSidebar";
import { useDetection } from "@/hooks/useDetection";
import type { MapStyle } from "@/types";
import type { MapViewHandle } from "@/components/map/MapView";

const MapView = dynamic(() => import("@/components/map/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#f0f1f3] flex items-center justify-center">
      <div className="flex items-center gap-2 text-[13px] text-[#9ca3af]">
        <div className="w-4 h-4 border-2 border-[#3b6fa0] border-t-transparent rounded-full animate-spin" />
        Loading map...
      </div>
    </div>
  ),
});

export default function Home() {
  const [mapStyle, setMapStyle] = useState<MapStyle>("satellite");
  const mapRef = useRef<MapViewHandle>(null);
  const {
    result,
    runCoordinateDetection,
    runImageDetection,
    runTimeSeries,
    runScanArea,
    clearResults,
  } = useDetection();
  const [pendingCoords, setPendingCoords] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [mapBounds, setMapBounds] = useState<{
    north: number;
    south: number;
    east: number;
    west: number;
  } | null>(null);

  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      setPendingCoords({ lat, lng });
      runCoordinateDetection(lat, lng);
      mapRef.current?.flyTo(lng, lat, 18);
    },
    [runCoordinateDetection]
  );

  const handleRunDetection = useCallback(() => {
    if (pendingCoords) {
      runCoordinateDetection(pendingCoords.lat, pendingCoords.lng);
    }
  }, [pendingCoords, runCoordinateDetection]);

  const handleFileSelected = useCallback(
    (file: File) => {
      runImageDetection(file);
    },
    [runImageDetection]
  );

  const handleRunTimeSeries = useCallback(() => {
    const coords = result.coordinates || pendingCoords;
    if (coords) {
      runTimeSeries(coords.lat, coords.lng);
    }
  }, [result.coordinates, pendingCoords, runTimeSeries]);

  const handleRunScanArea = useCallback(
    (north: number, south: number, east: number, west: number) => {
      runScanArea(north, south, east, west);
    },
    [runScanArea]
  );

  const handleBoundsChange = useCallback(
    (bounds: { north: number; south: number; east: number; west: number }) => {
      setMapBounds(bounds);
    },
    []
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopNav mapStyle={mapStyle} onStyleChange={setMapStyle} />
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar
          result={{
            ...result,
            coordinates: result.coordinates || pendingCoords,
          }}
          onFileSelected={handleFileSelected}
          onRunDetection={handleRunDetection}
          onRunTimeSeries={handleRunTimeSeries}
          onRunScanArea={handleRunScanArea}
          mapBounds={mapBounds}
        />
        <main className="flex-1 relative">
          <MapView
            ref={mapRef}
            mapStyle={mapStyle}
            onMapClick={handleMapClick}
            detections={result.detections}
            geoFeatures={result.geoFeatures}
            clickCoords={result.coordinates || pendingCoords}
            onBoundsChange={handleBoundsChange}
          />
          {pendingCoords && (
            <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm border border-[#e2e5ea] rounded-md px-3 py-1.5 text-[11px] text-[#6b7280] font-mono shadow-sm">
              {pendingCoords.lat.toFixed(6)}, {pendingCoords.lng.toFixed(6)}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
