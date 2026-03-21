import type { Commodity } from "../lib/api";
import clsx from "clsx";

interface Props {
  commodities: Commodity[];
}

function colorForPct(pct: number | null): string {
  if (pct === null) return "bg-gray-100 text-gray-400";
  if (pct >= 10) return "bg-red-600 text-white";
  if (pct >= 5)  return "bg-red-300 text-red-900";
  if (pct >= 2)  return "bg-amber-200 text-amber-900";
  if (pct >= 0)  return "bg-teal-100 text-teal-800";
  if (pct >= -5) return "bg-teal-300 text-teal-900";
  return "bg-teal-600 text-white";
}

export default function CommodityHeatmap({ commodities }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <h2 className="font-semibold text-gray-700 mb-1">Commodities</h2>
      <p className="text-xs text-gray-400 mb-4">% change windows — red = rising price pressure</p>
      <div className="space-y-3">
        {commodities.length === 0 ? (
          <p className="text-sm text-gray-400">Loading commodity data...</p>
        ) : (
          commodities.map((c) => (
            <div key={c.series_id} className="flex items-center gap-4">
              <div className="w-24 flex-shrink-0">
                <p className="text-sm font-medium text-gray-900">{c.name}</p>
                <p className="text-xs text-gray-400">{c.latest != null ? `${c.unit}: ${c.latest.toFixed(2)}` : "—"}</p>
              </div>
              <div className="flex gap-2 flex-1">
                {[
                  { label: "1M", pct: c.chg_1m_pct },
                  { label: "3M", pct: c.chg_3m_pct },
                ].map(({ label, pct }) => (
                  <div key={label} className={clsx("flex-1 rounded-lg p-2 text-center", colorForPct(pct))}>
                    <p className="text-[10px] font-medium uppercase">{label}</p>
                    <p className="text-sm font-bold">{pct != null ? `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%` : "—"}</p>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
