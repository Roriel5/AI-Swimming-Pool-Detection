"use client";

import type { RiskResult } from "@/types";

interface RiskPanelProps {
  risk: RiskResult;
}

const LEVEL_STYLES: Record<string, { bg: string; text: string; ring: string; dot: string }> = {
  Low: { bg: "bg-[#ecfdf5]", text: "text-[#065f46]", ring: "border-[#a7f3d0]", dot: "bg-[#10b981]" },
  Medium: { bg: "bg-[#fffbeb]", text: "text-[#92400e]", ring: "border-[#fde68a]", dot: "bg-[#f59e0b]" },
  High: { bg: "bg-[#fef2f2]", text: "text-[#991b1b]", ring: "border-[#fecaca]", dot: "bg-[#ef4444]" },
};

export default function RiskPanel({ risk }: RiskPanelProps) {
  const style = LEVEL_STYLES[risk.risk_level] || LEVEL_STYLES.Low;

  return (
    <div className="space-y-2.5">
      <h3 className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider">
        Risk Assessment
      </h3>

      {/* Score + Level badge */}
      <div className={`flex items-center justify-between p-3 rounded-md border ${style.bg} ${style.ring}`}>
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${style.dot}`} />
          <span className={`text-[13px] font-semibold ${style.text}`}>
            {risk.risk_level} Risk
          </span>
        </div>
        <span className={`text-[18px] font-bold ${style.text}`}>
          {risk.risk_score}
          <span className="text-[11px] font-normal">/100</span>
        </span>
      </div>

      {/* Score bar */}
      <div className="w-full h-2 bg-[#e5e7eb] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${risk.risk_score}%`,
            background:
              risk.risk_score >= 65
                ? "#ef4444"
                : risk.risk_score >= 40
                ? "#f59e0b"
                : "#10b981",
          }}
        />
      </div>

      {/* Factors */}
      {risk.risk_factors.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider">
            Factors
          </p>
          <ul className="space-y-1">
            {risk.risk_factors.map((f, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-[11px] text-[#6b7280]"
              >
                <span className="text-[#d1d5db] mt-px">•</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
