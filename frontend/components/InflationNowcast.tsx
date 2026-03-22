"use client";
import useSWR from "swr";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from "recharts";
import { api, CpiComponent } from "../lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  total: "#60a5fa",
  core: "#818cf8",
  food: "#fb923c",
  energy: "#facc15",
  goods: "#34d399",
  services: "#a78bfa",
};

const CATEGORY_LABELS: Record<string, string> = {
  total: "Total", core: "Core", food: "Food",
  energy: "Energy", goods: "Goods", services: "Services",
};

function TooltipContent({ active, payload }: { active?: boolean; payload?: { payload: CpiComponent }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold text-white mb-1">{d.label}</p>
      <p className="text-gray-300">YoY: <span className={d.yoy_pct && d.yoy_pct > 0 ? "text-orange-400" : "text-blue-400"}>
        {d.yoy_pct != null ? `${d.yoy_pct > 0 ? "+" : ""}${d.yoy_pct.toFixed(1)}%` : "N/A"}
      </span></p>
      {d.mom_pct != null && (
        <p className="text-gray-400">MoM: {d.mom_pct > 0 ? "+" : ""}{d.mom_pct.toFixed(2)}%</p>
      )}
      <p className="text-gray-500 capitalize mt-1">Category: {CATEGORY_LABELS[d.category] ?? d.category}</p>
    </div>
  );
}

function CategoryPill({ cat, value }: { cat: string; value: number }) {
  const color = CATEGORY_COLORS[cat] ?? "#9ca3af";
  const hot = value > 3;
  const cold = value < 0;
  return (
    <div
      className={`flex flex-col items-center rounded-xl p-3 border ${
        hot ? "border-orange-600 bg-orange-900/20" : cold ? "border-blue-700 bg-blue-900/20" : "border-gray-700 bg-gray-700/30"
      }`}
    >
      <span className="text-[10px] text-gray-400 uppercase tracking-wider">{CATEGORY_LABELS[cat] ?? cat}</span>
      <span
        className="text-lg font-bold mt-0.5"
        style={{ color }}
      >
        {value > 0 ? "+" : ""}{value.toFixed(1)}%
      </span>
    </div>
  );
}

export default function InflationNowcast() {
  const { data, isLoading, error } = useSWR("inflation-nowcast", api.inflationNowcast, {
    refreshInterval: 300_000,
    revalidateOnFocus: false,
  });

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700 flex items-center justify-center h-64">
        <span className="text-gray-500 text-sm">Loading inflation nowcast…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
        <p className="text-red-400 text-sm">Inflation nowcast unavailable.</p>
      </div>
    );
  }

  const { components, category_summary, as_of } = data;

  // Filter only components with data, skip duplicates for chart
  const chartData = components
    .filter((c) => c.yoy_pct != null && c.label !== "Headline CPI")
    .slice(0, 10);

  const headline = components.find((c) => c.label === "Headline CPI");
  const core = components.find((c) => c.label === "Core CPI");

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-sm font-semibold text-white">US Inflation Nowcast</h2>
        <span className="text-[11px] text-gray-500">as of {as_of}</span>
      </div>
      <p className="text-[11px] text-gray-400 mb-4">Year-over-year % change by CPI component</p>

      {/* Headline pills */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-5">
        {headline?.yoy_pct != null && (
          <div className="col-span-2 sm:col-span-1 flex flex-col items-center rounded-xl p-3 border border-blue-600 bg-blue-900/20">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">Headline</span>
            <span className="text-xl font-bold text-blue-400 mt-0.5">
              {headline.yoy_pct > 0 ? "+" : ""}{headline.yoy_pct.toFixed(1)}%
            </span>
          </div>
        )}
        {core?.yoy_pct != null && (
          <div className="col-span-2 sm:col-span-1 flex flex-col items-center rounded-xl p-3 border border-indigo-600 bg-indigo-900/20">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">Core</span>
            <span className="text-xl font-bold text-indigo-400 mt-0.5">
              {core.yoy_pct > 0 ? "+" : ""}{core.yoy_pct.toFixed(1)}%
            </span>
          </div>
        )}
        {Object.entries(category_summary)
          .filter(([cat]) => !["total", "core"].includes(cat))
          .slice(0, 4)
          .map(([cat, val]) => (
            <CategoryPill key={cat} cat={cat} value={val} />
          ))}
      </div>

      {/* Bar chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 0, right: 24, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
            <XAxis
              type="number"
              domain={["auto", "auto"]}
              tick={{ fontSize: 10, fill: "#9ca3af" }}
              tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={110}
              tick={{ fontSize: 10, fill: "#d1d5db" }}
            />
            <Tooltip content={<TooltipContent />} />
            <ReferenceLine x={2} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1.5} />
            <ReferenceLine x={0} stroke="#6b7280" strokeWidth={1} />
            <Bar dataKey="yoy_pct" radius={[0, 4, 4, 0]} maxBarSize={16}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    entry.yoy_pct == null
                      ? "#4b5563"
                      : entry.yoy_pct > 4
                      ? "#ef4444"
                      : entry.yoy_pct > 2
                      ? "#f97316"
                      : entry.yoy_pct < 0
                      ? "#3b82f6"
                      : "#10b981"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="text-sm text-gray-500 py-6 text-center">
          Run the data fetch to populate CPI components.
        </div>
      )}

      <p className="text-[10px] text-gray-600 mt-2">
        Red dashed line = 2% Fed target. Source: BLS via FRED.
      </p>
    </div>
  );
}
