import type { RegimeData } from "../lib/api";
import clsx from "clsx";

interface Props {
  regime: RegimeData | null;
}

const COLORS = {
  teal:   { bg: "bg-teal-50",   border: "border-teal-400",   badge: "bg-teal-600 text-white",   dot: "bg-teal-500" },
  amber:  { bg: "bg-amber-50",  border: "border-amber-400",  badge: "bg-amber-600 text-white",  dot: "bg-amber-500" },
  coral:  { bg: "bg-red-50",    border: "border-red-400",    badge: "bg-red-700 text-white",    dot: "bg-red-600" },
  purple: { bg: "bg-purple-50", border: "border-purple-400", badge: "bg-purple-700 text-white", dot: "bg-purple-600" },
};

const QUADRANT_LABELS = [
  { q: "REFLATION",   pos: "top-2 left-2",   label: "Reflation" },
  { q: "GOLDILOCKS",  pos: "top-2 right-2",  label: "Goldilocks" },
  { q: "STAGFLATION", pos: "bottom-2 left-2", label: "Stagflation" },
  { q: "DEFLATION",   pos: "bottom-2 right-2", label: "Deflation" },
];

export default function RegimeQuadrant({ regime }: Props) {
  const color = COLORS[regime?.color ?? "teal"];
  const indicators = regime?.indicators;

  // Position dot in the 2×2 grid:
  // x-axis = inflation (left=low, right=high), y-axis = growth (top=high, bottom=low)
  const dotX = indicators?.high_inflation ? 75 : 25;
  const dotY = indicators?.gdp_growing ? 25 : 75;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-700">Macro Regime</h2>
        {regime && (
          <span className={clsx("text-xs font-bold px-3 py-1 rounded-full", color.badge)}>
            {regime.quadrant}
          </span>
        )}
      </div>

      {/* 2×2 quadrant grid */}
      <div className="relative w-full aspect-square border border-gray-200 rounded-lg overflow-hidden mb-4">
        {/* Quadrant backgrounds */}
        <div className="absolute inset-0 grid grid-cols-2 grid-rows-2">
          <div className="bg-amber-50 border-r border-b border-gray-200" />
          <div className="bg-teal-50 border-b border-gray-200" />
          <div className="bg-red-50 border-r border-gray-200" />
          <div className="bg-purple-50" />
        </div>
        {/* Axis labels */}
        <div className="absolute top-1/2 left-0 -translate-y-1/2 -translate-x-0 text-[9px] text-gray-400 font-medium pl-1">▲ Growth</div>
        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] text-gray-400 font-medium">Inflation ▶</div>
        {/* Quadrant labels */}
        {QUADRANT_LABELS.map(({ q, pos, label }) => (
          <span
            key={q}
            className={clsx(
              "absolute text-[10px] font-semibold px-1",
              pos,
              regime?.quadrant === q ? "text-gray-800" : "text-gray-400"
            )}
          >
            {label}
          </span>
        ))}
        {/* Dot */}
        {regime && (
          <div
            className={clsx("absolute h-4 w-4 rounded-full -translate-x-1/2 -translate-y-1/2 shadow-md ring-2 ring-white", color.dot)}
            style={{ left: `${dotX}%`, top: `${dotY}%` }}
          />
        )}
      </div>

      <p className="text-xs text-gray-500 mb-3">{regime?.description ?? "Loading..."}</p>

      {/* Supporting indicators */}
      <div className="space-y-1.5">
        {[
          { label: "GDP QoQ", value: indicators?.gdp_qoq_pct != null ? `${indicators.gdp_qoq_pct.toFixed(1)}%` : "—" },
          { label: "CPI YoY", value: indicators?.cpi_yoy_pct != null ? `${indicators.cpi_yoy_pct.toFixed(1)}%` : "—" },
          { label: "Sahm Rule", value: indicators?.sahm_rule != null ? indicators.sahm_rule.toFixed(2) : "—" },
          { label: "Yield Curve", value: indicators?.yield_curve_spread != null ? `${indicators.yield_curve_spread.toFixed(2)}%` : "—" },
          { label: "Fed Funds", value: indicators?.fed_funds != null ? `${indicators.fed_funds.toFixed(2)}%` : "—" },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between text-xs">
            <span className="text-gray-500">{label}</span>
            <span className="font-medium text-gray-800">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
