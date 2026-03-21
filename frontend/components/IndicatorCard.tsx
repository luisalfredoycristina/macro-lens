import type { Indicator } from "../lib/api";
import clsx from "clsx";

interface Props {
  indicator: Indicator;
}

function formatValue(val: number | null, seriesId: string): string {
  if (val === null) return "—";
  if (seriesId.includes("M2SL")) return `$${(val / 1000).toFixed(1)}T`;
  if (["CPIAUCSL", "PCEPI", "UNRATE", "FEDFUNDS", "T10Y2Y",
       "DGS3MO","DGS2","DGS5","DGS10","DGS30","T10YIE","SAHMREALTIME"].includes(seriesId))
    return `${val.toFixed(2)}%`;
  if (seriesId === "GOLDAMGBD228NLBM") return `$${val.toFixed(0)}`;
  if (seriesId === "DCOILWTICO") return `$${val.toFixed(2)}`;
  if (seriesId === "GDPC1") return `$${(val / 1000).toFixed(0)}B`;
  return val.toFixed(2);
}

export default function IndicatorCard({ indicator }: Props) {
  const isUp = indicator.trend === "up";
  const isDown = indicator.trend === "down";
  const isPositiveUp = !["UNRATE", "T10Y2Y", "SAHMREALTIME", "CPIAUCSL", "PCEPI", "PPIACO"].includes(indicator.series_id);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow">
      <p className="text-xs text-gray-500 font-medium mb-1 truncate">{indicator.name}</p>
      <p className="text-2xl font-bold text-gray-900 mb-1">
        {formatValue(indicator.latest, indicator.series_id)}
      </p>
      <div className="flex items-center gap-1">
        {indicator.delta_pct !== null && (
          <>
            <span className={clsx(
              "text-xs font-semibold",
              isUp && isPositiveUp ? "text-teal-600" :
              isUp && !isPositiveUp ? "text-red-600" :
              isDown && isPositiveUp ? "text-red-600" :
              isDown && !isPositiveUp ? "text-teal-600" :
              "text-gray-500"
            )}>
              {isUp ? "▲" : isDown ? "▼" : "—"}{" "}
              {Math.abs(indicator.delta_pct).toFixed(2)}%
            </span>
            <span className="text-xs text-gray-400">vs prior</span>
          </>
        )}
      </div>
      <p className="text-[10px] text-gray-400 mt-1 uppercase tracking-wide">{indicator.series_id}</p>
    </div>
  );
}
