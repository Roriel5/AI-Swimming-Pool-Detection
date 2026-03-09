"use client";

import { MapStyle } from "@/types";

interface TopNavProps {
  mapStyle: MapStyle;
  onStyleChange: (style: MapStyle) => void;
}

export default function TopNav({ mapStyle, onStyleChange }: TopNavProps) {
  return (
    <header className="h-12 bg-white border-b border-[#e2e5ea] flex items-center justify-between px-4 shrink-0 z-50">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b6fa0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <span className="text-sm font-semibold text-[#1a1d23] tracking-tight">
            AquaVision
          </span>
        </div>
        <span className="text-[11px] text-[#9ca3af] font-normal ml-1 hidden sm:inline">
          Pool Detection Analytics
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Map style toggle */}
        <div className="flex items-center bg-[#f3f4f6] rounded-md p-0.5">
          <button
            onClick={() => onStyleChange("satellite")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              mapStyle === "satellite"
                ? "bg-white text-[#1a1d23] shadow-sm"
                : "text-[#6b7280] hover:text-[#374151]"
            }`}
          >
            Satellite
          </button>
          <button
            onClick={() => onStyleChange("streets")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              mapStyle === "streets"
                ? "bg-white text-[#1a1d23] shadow-sm"
                : "text-[#6b7280] hover:text-[#374151]"
            }`}
          >
            Streets
          </button>
        </div>

        {/* User menu placeholder */}
        <div className="w-7 h-7 rounded-full bg-[#e5e7eb] flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      </div>
    </header>
  );
}
