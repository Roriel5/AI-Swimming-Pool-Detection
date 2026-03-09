"use client";

import type { TimeSeriesResponse } from "@/types";

interface TimeSeriesPanelProps {
  data: TimeSeriesResponse | null;
  loading: boolean;
  onRun: () => void;
  canRun: boolean;
}

export default function TimeSeriesPanel({
  data,
  loading,
  onRun,
  canRun,
}: TimeSeriesPanelProps) {
  return (
    <div className="space-y-2.5">
      <h3 className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider">
        Change Detection
      </h3>

      <button
        onClick={onRun}
        disabled={!canRun || loading}
        className={`w-full py-2 px-3 rounded-md text-[12px] font-medium transition-colors ${
          canRun && !loading
            ? "bg-[#1e3a5f] text-white hover:bg-[#162d4d] active:bg-[#0f2038]"
            : "bg-[#f3f4f6] text-[#9ca3af] cursor-not-allowed"
        }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Analyzing changes...
          </span>
        ) : (
          "Run Change Detection"
        )}
      </button>

      {data && (
        <div className="space-y-2">
          {/* Change indicator */}
          <div
            className={`flex items-center gap-2 p-2.5 rounded-md ${
              data.change_detected
                ? "bg-[#fffbeb] border border-[#fde68a]"
                : "bg-[#ecfdf5] border border-[#a7f3d0]"
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                data.change_detected ? "bg-[#f59e0b]" : "bg-[#10b981]"
              }`}
            />
            <span className="text-[12px] font-medium text-[#1a1d23]">
              {data.change_detected ? "Changes Detected" : "No Changes"}
            </span>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-2">
            <StatCard
              label="Current Pools"
              value={String(data.current_pool_count ?? data.current_count ?? "–")}
            />
            <StatCard
              label="Previous Pools"
              value={String(data.previous_pool_count ?? data.historical_count ?? "–")}
            />
            <StatCard
              label="Added"
              value={`+${data.pools_added}`}
              highlight={data.pools_added > 0}
              color="text-[#059669]"
            />
            <StatCard
              label="Removed"
              value={`-${data.pools_removed}`}
              highlight={data.pools_removed > 0}
              color="text-[#dc2626]"
            />
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight,
  color,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  color?: string;
}) {
  return (
    <div className="p-2.5 bg-[#fafbfc] border border-[#e2e5ea] rounded-md">
      <p className="text-[10px] text-[#9ca3af] uppercase tracking-wider">{label}</p>
      <p
        className={`text-[14px] font-semibold mt-0.5 ${
          highlight && color ? color : "text-[#1a1d23]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
