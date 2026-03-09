"use client";

import { useState } from "react";
import type { ScanAreaResponse, RiskResult } from "@/types";

interface ScanAreaPanelProps {
  scanResult: ScanAreaResponse | null;
  loading: boolean;
  onRun: (north: number, south: number, east: number, west: number) => void;
  mapBounds: { north: number; south: number; east: number; west: number } | null;
}

export default function ScanAreaPanel({
  scanResult,
  loading,
  onRun,
  mapBounds,
}: ScanAreaPanelProps) {
  const [useMapBounds, setUseMapBounds] = useState(true);
  const [north, setNorth] = useState("");
  const [south, setSouth] = useState("");
  const [east, setEast] = useState("");
  const [west, setWest] = useState("");

  const handleRun = () => {
    if (useMapBounds && mapBounds) {
      onRun(mapBounds.north, mapBounds.south, mapBounds.east, mapBounds.west);
    } else {
      const n = parseFloat(north);
      const s = parseFloat(south);
      const e = parseFloat(east);
      const w = parseFloat(west);
      if ([n, s, e, w].some(isNaN)) return;
      onRun(n, s, e, w);
    }
  };

  const canRun =
    !loading &&
    (useMapBounds
      ? mapBounds !== null
      : [north, south, east, west].every((v) => v.trim() !== ""));

  return (
    <div className="space-y-2.5">
      <h3 className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider">
        Area Scan
      </h3>

      {/* Bounds source toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={useMapBounds}
          onChange={(e) => setUseMapBounds(e.target.checked)}
          className="w-3.5 h-3.5 rounded border-[#d1d5db] text-[#3b6fa0] focus:ring-[#3b6fa0] focus:ring-1"
        />
        <span className="text-[12px] text-[#374151]">Use current map viewport</span>
      </label>

      {/* Manual input */}
      {!useMapBounds && (
        <div className="grid grid-cols-2 gap-1.5">
          <CoordInput label="North" value={north} onChange={setNorth} />
          <CoordInput label="South" value={south} onChange={setSouth} />
          <CoordInput label="East" value={east} onChange={setEast} />
          <CoordInput label="West" value={west} onChange={setWest} />
        </div>
      )}

      {useMapBounds && mapBounds && (
        <div className="text-[10px] text-[#6b7280] font-mono bg-[#f9fafb] border border-[#e2e5ea] rounded p-2 leading-relaxed">
          N {mapBounds.north.toFixed(5)} &middot; S {mapBounds.south.toFixed(5)}
          <br />
          E {mapBounds.east.toFixed(5)} &middot; W {mapBounds.west.toFixed(5)}
        </div>
      )}

      <button
        onClick={handleRun}
        disabled={!canRun}
        className={`w-full py-2 px-3 rounded-md text-[12px] font-medium transition-colors ${
          canRun
            ? "bg-[#065f46] text-white hover:bg-[#064e3b] active:bg-[#033b2e]"
            : "bg-[#f3f4f6] text-[#9ca3af] cursor-not-allowed"
        }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Scanning area...
          </span>
        ) : (
          "Scan Visible Area"
        )}
      </button>

      {/* Results */}
      {scanResult && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 p-2.5 rounded-md bg-[#e8f0f8]">
            <div className="w-2 h-2 rounded-full bg-[#3b6fa0]" />
            <span className="text-[12px] font-medium text-[#1a1d23]">
              {scanResult.pools_detected} pool{scanResult.pools_detected !== 1 ? "s" : ""} found
            </span>
            <span className="text-[10px] text-[#6b7280] ml-auto">
              {scanResult.tiles_scanned} tile{scanResult.tiles_scanned !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Scan risk */}
          {scanResult.risk && (
            <ScanRiskBadge risk={scanResult.risk} />
          )}
        </div>
      )}
    </div>
  );
}

function CoordInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="text-[10px] text-[#9ca3af] uppercase tracking-wider">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="0.000"
        className="w-full mt-0.5 px-2 py-1.5 text-[11px] font-mono border border-[#e2e5ea] rounded bg-white focus:outline-none focus:border-[#3b6fa0]"
      />
    </div>
  );
}

function ScanRiskBadge({ risk }: { risk: RiskResult }) {
  const colors: Record<string, string> = {
    Low: "bg-[#ecfdf5] text-[#065f46] border-[#a7f3d0]",
    Medium: "bg-[#fffbeb] text-[#92400e] border-[#fde68a]",
    High: "bg-[#fef2f2] text-[#991b1b] border-[#fecaca]",
  };
  const cls = colors[risk.risk_level] || colors.Low;

  return (
    <div className={`flex items-center justify-between p-2.5 rounded-md border ${cls}`}>
      <span className="text-[12px] font-medium">{risk.risk_level} Risk</span>
      <span className="text-[14px] font-bold">
        {risk.risk_score}<span className="text-[10px] font-normal">/100</span>
      </span>
    </div>
  );
}
