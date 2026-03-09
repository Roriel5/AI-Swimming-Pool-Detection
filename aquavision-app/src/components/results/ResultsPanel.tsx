"use client";

import type { AnalysisResult } from "@/types";

interface ResultsPanelProps {
  result: AnalysisResult;
}

const POOL_TYPE_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  in_ground: { label: "In-ground", bg: "bg-[#e0f7fa]", text: "text-[#006064]" },
  above_ground: { label: "Above-ground", bg: "bg-[#fff8e1]", text: "text-[#e65100]" },
  covered: { label: "Covered", bg: "bg-[#ede7f6]", text: "text-[#4527a0]" },
  uncovered: { label: "Uncovered", bg: "bg-[#e0f7fa]", text: "text-[#006064]" },
};

export default function ResultsPanel({ result }: ResultsPanelProps) {
  const { detections, geoFeatures, coordinates, loading, error, source } = result;
  const hasDetections = detections.length > 0;
  const totalPools = detections.length;
  const avgConfidence =
    hasDetections
      ? detections.reduce((s, d) => s + d.confidence, 0) / totalPools
      : 0;
  const maxConfidence = hasDetections
    ? Math.max(...detections.map((d) => d.confidence))
    : 0;

  // Count pool types from geoFeatures
  const typeCounts: Record<string, number> = {};
  for (const f of geoFeatures) {
    const t = f.properties?.pool_type || "unknown";
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider">
          Analysis
        </h3>
        <div className="flex items-center gap-2 py-6 justify-center">
          <div className="w-4 h-4 border-2 border-[#3b6fa0] border-t-transparent rounded-full animate-spin" />
          <span className="text-[12px] text-[#6b7280]">Running detection...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider">
          Analysis
        </h3>
        <div className="bg-[#fef2f2] border border-[#fecaca] rounded-md p-3">
          <p className="text-[12px] text-[#dc2626]">{error}</p>
        </div>
      </div>
    );
  }

  if (!source) {
    return (
      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider">
          Analysis
        </h3>
        <p className="text-[12px] text-[#9ca3af] py-4 text-center">
          Click on the map or upload an image to start detection.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider">
        Analysis Results
      </h3>

      {/* Status */}
      <div className={`flex items-center gap-2 p-2.5 rounded-md ${
        hasDetections ? "bg-[#e8f0f8]" : "bg-[#f3f4f6]"
      }`}>
        <div className={`w-2 h-2 rounded-full ${hasDetections ? "bg-[#3b6fa0]" : "bg-[#9ca3af]"}`} />
        <span className="text-[12px] font-medium text-[#1a1d23]">
          {hasDetections
            ? `${totalPools} pool${totalPools > 1 ? "s" : ""} detected`
            : "No pools detected"}
        </span>
      </div>

      {/* Pool type breakdown */}
      {Object.keys(typeCounts).length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(typeCounts).map(([type, count]) => {
            const style = POOL_TYPE_STYLES[type] || { label: type, bg: "bg-[#f3f4f6]", text: "text-[#6b7280]" };
            return (
              <span
                key={type}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${style.bg} ${style.text}`}
              >
                {style.label}
                {count > 1 && <span className="font-bold">&times;{count}</span>}
              </span>
            );
          })}
        </div>
      )}

      {/* Coordinates */}
      {coordinates && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider">Location</p>
          <p className="text-[12px] text-[#374151] font-mono">
            {coordinates.lat.toFixed(6)}, {coordinates.lng.toFixed(6)}
          </p>
        </div>
      )}

      {/* Metrics */}
      {hasDetections && (
        <div className="grid grid-cols-2 gap-2">
          <MetricCard label="Pools Found" value={String(totalPools)} />
          <MetricCard label="Max Confidence" value={`${(maxConfidence * 100).toFixed(1)}%`} />
          <MetricCard label="Avg Confidence" value={`${(avgConfidence * 100).toFixed(1)}%`} />
          <MetricCard
            label="Risk Level"
            value={result.risk?.risk_level || (totalPools >= 2 ? "Elevated" : "Standard")}
            highlight={result.risk ? result.risk.risk_level !== "Low" : totalPools >= 2}
          />
        </div>
      )}

      {/* Individual detections */}
      {hasDetections && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider">Detections</p>
          {detections.map((d, i) => {
            const feat = geoFeatures[i];
            const poolType = feat?.properties?.pool_type;
            const typeStyle = poolType ? POOL_TYPE_STYLES[poolType] : null;

            return (
              <div
                key={i}
                className="flex items-center justify-between p-2.5 bg-[#fafbfc] border border-[#e2e5ea] rounded-md"
              >
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-[#e8f0f8] flex items-center justify-center text-[10px] font-semibold text-[#3b6fa0]">
                    {i + 1}
                  </div>
                  <span className="text-[12px] text-[#374151]">Pool</span>
                  {typeStyle && (
                    <span className={`text-[9px] px-1.5 py-px rounded-full font-medium ${typeStyle.bg} ${typeStyle.text}`}>
                      {typeStyle.label}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <ConfidenceBar value={d.confidence} />
                  <span className="text-[11px] font-mono text-[#6b7280] w-12 text-right">
                    {(d.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="p-2.5 bg-[#fafbfc] border border-[#e2e5ea] rounded-md">
      <p className="text-[10px] text-[#9ca3af] uppercase tracking-wider">{label}</p>
      <p className={`text-[14px] font-semibold mt-0.5 ${highlight ? "text-[#b45309]" : "text-[#1a1d23]"}`}>
        {value}
      </p>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="w-16 h-1.5 bg-[#e5e7eb] rounded-full overflow-hidden">
      <div
        className="h-full bg-[#3b6fa0] rounded-full transition-all"
        style={{ width: `${value * 100}%` }}
      />
    </div>
  );
}
