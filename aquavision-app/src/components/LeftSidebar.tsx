"use client";

import type { AnalysisResult } from "@/types";
import UploadPanel from "@/components/upload/UploadPanel";
import ResultsPanel from "@/components/results/ResultsPanel";
import RiskPanel from "@/components/results/RiskPanel";
import TimeSeriesPanel from "@/components/results/TimeSeriesPanel";
import ScanAreaPanel from "@/components/results/ScanAreaPanel";

interface LeftSidebarProps {
  result: AnalysisResult;
  onFileSelected: (file: File) => void;
  onRunDetection: () => void;
  onRunTimeSeries: () => void;
  onRunScanArea: (north: number, south: number, east: number, west: number) => void;
  mapBounds: { north: number; south: number; east: number; west: number } | null;
}

export default function LeftSidebar({
  result,
  onFileSelected,
  onRunDetection,
  onRunTimeSeries,
  onRunScanArea,
  mapBounds,
}: LeftSidebarProps) {
  const canRun = result.coordinates !== null && !result.loading;
  const hasDetections = result.detections.length > 0;

  return (
    <aside className="w-[320px] bg-white border-r border-[#e2e5ea] flex flex-col shrink-0 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Upload section */}
        <UploadPanel onFileSelected={onFileSelected} loading={result.loading && result.source === "upload"} />

        {/* Coordinate detection */}
        <div className="space-y-3">
          <h3 className="text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider">
            Map Detection
          </h3>
          <p className="text-[12px] text-[#9ca3af]">
            Click any location on the map to analyze for swimming pools.
          </p>
          {result.coordinates && (
            <div className="text-[11px] text-[#374151] font-mono bg-[#f9fafb] border border-[#e2e5ea] rounded px-2.5 py-1.5">
              {result.coordinates.lat.toFixed(6)}, {result.coordinates.lng.toFixed(6)}
            </div>
          )}
          <button
            onClick={onRunDetection}
            disabled={!canRun}
            className={`w-full py-2 px-3 rounded-md text-[12px] font-medium transition-colors ${
              canRun
                ? "bg-[#3b6fa0] text-white hover:bg-[#2f5a82] active:bg-[#264a6d]"
                : "bg-[#f3f4f6] text-[#9ca3af] cursor-not-allowed"
            }`}
          >
            {result.loading && result.source === "coordinates"
              ? "Detecting..."
              : "Run Detection"}
          </button>
        </div>

        {/* Divider */}
        <div className="border-t border-[#e2e5ea]" />

        {/* Results */}
        <ResultsPanel result={result} />

        {/* Risk Assessment */}
        {hasDetections && result.risk && (
          <>
            <div className="border-t border-[#e2e5ea]" />
            <RiskPanel risk={result.risk} />
          </>
        )}

        {/* Change Detection */}
        {result.source === "coordinates" && hasDetections && (
          <>
            <div className="border-t border-[#e2e5ea]" />
            <TimeSeriesPanel
              data={result.timeSeries}
              loading={result.timeSeriesLoading}
              onRun={onRunTimeSeries}
              canRun={result.coordinates !== null}
            />
          </>
        )}

        {/* Divider */}
        <div className="border-t border-[#e2e5ea]" />

        {/* Area Scan */}
        <ScanAreaPanel
          scanResult={result.scanResult}
          loading={result.scanLoading}
          onRun={onRunScanArea}
          mapBounds={mapBounds}
        />
      </div>

      {/* Footer */}
      <div className="border-t border-[#e2e5ea] px-4 py-2.5">
        <p className="text-[10px] text-[#9ca3af]">
          Model: YOLOv11m &middot; Satellite imagery
        </p>
      </div>
    </aside>
  );
}
