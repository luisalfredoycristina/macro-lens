"use client";
import useSWR from "swr";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from "recharts";
import { api, FomcAnalysis } from "../lib/api";

// Hawk-dove arc meter
function PolicyMeter({ score }: { score: number }) {
  // score: 0=fully dovish, 50=neutral, 100=fully hawkish
  const clamp = Math.max(0, Math.min(100, score));
  const angle = -90 + (clamp / 100) * 180; // -90° to +90°
  const toRad = (d: number) => (d * Math.PI) / 180;
  const cx = 60, cy = 56, r = 44;

  // Needle tip
  const tipX = cx + r * Math.cos(toRad(angle));
  const tipY = cy + r * Math.sin(toRad(angle));

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 70" width={140} height={84}>
        {/* Arc background */}
        <path
          d="M 16 56 A 44 44 0 0 1 104 56"
          fill="none" stroke="#374151" strokeWidth={10} strokeLinecap="round"
        />
        {/* Dovish zone (left) */}
        <path
          d="M 16 56 A 44 44 0 0 1 60 12"
          fill="none" stroke="#3b82f6" strokeWidth={10} strokeLinecap="round" opacity={0.6}
        />
        {/* Neutral zone (middle) */}
        <path
          d="M 60 12 A 44 44 0 0 1 86 21"
          fill="none" stroke="#6b7280" strokeWidth={10} opacity={0.6}
        />
        {/* Hawkish zone (right) */}
        <path
          d="M 86 21 A 44 44 0 0 1 104 56"
          fill="none" stroke="#ef4444" strokeWidth={10} strokeLinecap="round" opacity={0.6}
        />
        {/* Needle */}
        <line
          x1={cx} y1={cy}
          x2={tipX} y2={tipY}
          stroke="white" strokeWidth={2} strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={4} fill="white" />
      </svg>
      <div className="flex justify-between w-36 -mt-1 text-[10px]">
        <span className="text-blue-400 font-semibold">DOVISH</span>
        <span className="text-gray-400">NEUTRAL</span>
        <span className="text-red-400 font-semibold">HAWKISH</span>
      </div>
    </div>
  );
}

function MetricTile({ label, value, unit = "", color = "text-white" }: {
  label: string; value: string | number | null; unit?: string; color?: string;
}) {
  return (
    <div className="bg-gray-700/40 rounded-xl p-3 border border-gray-600">
      <p className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</p>
      <p className={`text-lg font-bold mt-0.5 ${color}`}>
        {value != null ? `${value}${unit}` : "—"}
      </p>
    </div>
  );
}

export default function FOMCAnalysis() {
  const { data, isLoading, error } = useSWR("fomc", api.fomc, {
    refreshInterval: 3_600_000,
    revalidateOnFocus: false,
  });

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700 flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-gray-500 text-sm mb-2">Fetching FOMC minutes from Federal Reserve…</div>
          <div className="text-gray-600 text-xs">This may take 10-15 seconds</div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
        <p className="text-red-400 text-sm">FOMC analysis unavailable.</p>
      </div>
    );
  }

  const { meeting_date, minutes_url, analysis, macro_context: ctx } = data;

  const stanceColor =
    analysis.stance === "HAWKISH"
      ? "text-red-400"
      : analysis.stance === "DOVISH"
      ? "text-blue-400"
      : "text-gray-300";

  // Build rate history chart data
  const rateHistory = ctx.fed_funds_history.map((p, i) => ({
    i: i + 1,
    rate: p.value,
  }));

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h2 className="text-sm font-semibold text-white">FOMC Minutes Analysis</h2>
          <p className="text-[11px] text-gray-400 mt-0.5">
            Meeting: {meeting_date || "Latest available"}
          </p>
          {minutes_url && (
            <a
              href={minutes_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] text-blue-400 hover:text-blue-300 underline"
            >
              View original minutes ↗
            </a>
          )}
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-bold border ${
          analysis.stance === "HAWKISH"
            ? "border-red-600 bg-red-900/30 text-red-300"
            : analysis.stance === "DOVISH"
            ? "border-blue-600 bg-blue-900/30 text-blue-300"
            : "border-gray-600 bg-gray-700/30 text-gray-300"
        }`}>
          {analysis.stance}
        </div>
      </div>

      {/* Meter + Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-5">
        {/* Meter */}
        <div className="flex flex-col items-center justify-center bg-gray-700/30 rounded-xl p-4 border border-gray-600">
          <PolicyMeter score={analysis.stance_score} />
          <div className="mt-3 flex gap-4 text-[11px]">
            <span className="text-red-400">
              🦅 Hawkish signals: <strong>{analysis.hawkish_count}</strong>
            </span>
            <span className="text-blue-400">
              🕊 Dovish signals: <strong>{analysis.dovish_count}</strong>
            </span>
          </div>
          {analysis.hawkish_terms_found.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1 justify-center">
              {analysis.hawkish_terms_found.map((t, i) => (
                <span key={i} className="text-[9px] bg-red-900/40 text-red-300 border border-red-800 px-1.5 py-0.5 rounded-full">
                  {t}
                </span>
              ))}
              {analysis.dovish_terms_found.map((t, i) => (
                <span key={i} className="text-[9px] bg-blue-900/40 text-blue-300 border border-blue-800 px-1.5 py-0.5 rounded-full">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Macro context metrics */}
        <div className="grid grid-cols-2 gap-2">
          <MetricTile
            label="Fed Funds Rate"
            value={ctx.fed_funds_rate?.toFixed(2) ?? null}
            unit="%"
            color="text-blue-300"
          />
          <MetricTile
            label="CPI YoY"
            value={ctx.cpi_yoy_pct?.toFixed(1) ?? null}
            unit="%"
            color={
              ctx.cpi_yoy_pct != null && ctx.cpi_yoy_pct > 3
                ? "text-red-400"
                : ctx.cpi_yoy_pct != null && ctx.cpi_yoy_pct < 1.5
                ? "text-blue-400"
                : "text-yellow-400"
            }
          />
          <MetricTile
            label="Core CPI YoY"
            value={ctx.core_cpi_yoy_pct?.toFixed(1) ?? null}
            unit="%"
            color="text-orange-300"
          />
          <MetricTile
            label="10Y Breakeven"
            value={ctx.breakeven_inflation_10y?.toFixed(2) ?? null}
            unit="%"
            color="text-purple-300"
          />
          <MetricTile
            label="Yield Spread"
            value={ctx.yield_curve_spread?.toFixed(2) ?? null}
            unit="%"
            color={
              ctx.yield_curve_spread != null && ctx.yield_curve_spread < 0
                ? "text-red-400"
                : "text-green-400"
            }
          />
          <MetricTile
            label="Unemployment"
            value={ctx.unemployment_rate?.toFixed(1) ?? null}
            unit="%"
            color="text-gray-200"
          />
        </div>
      </div>

      {/* Fed Funds Rate chart */}
      {rateHistory.length > 1 && (
        <div className="mb-5">
          <p className="text-[11px] text-gray-400 mb-2">Fed Funds Rate — last 12 months</p>
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={rateHistory} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="i" hide />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                tickFormatter={(v) => `${v}%`}
                width={36}
              />
              <Tooltip
                formatter={(v: number) => [`${v.toFixed(2)}%`, "Fed Funds"]}
                contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
                labelStyle={{ display: "none" }}
              />
              <ReferenceLine
                y={ctx.cpi_yoy_pct ?? 0}
                stroke="#f97316"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
              <Line
                type="stepAfter"
                dataKey="rate"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex items-center gap-2 mt-1">
            <span className="flex items-center gap-1 text-[10px] text-gray-500">
              <span className="w-4 h-0.5 bg-blue-400 inline-block" /> Fed Funds
            </span>
            <span className="flex items-center gap-1 text-[10px] text-gray-500">
              <span className="w-4 h-0.5 bg-orange-400 inline-block border-dashed" /> CPI YoY
            </span>
          </div>
        </div>
      )}

      {/* Key quotes */}
      {analysis.key_quotes.length > 0 && (
        <div>
          <p className="text-[11px] text-gray-400 uppercase tracking-wider mb-2">Key Passages</p>
          <div className="space-y-2">
            {analysis.key_quotes.slice(0, 4).map((q, i) => (
              <blockquote
                key={i}
                className="border-l-2 border-blue-600 pl-3 text-xs text-gray-300 leading-relaxed italic"
              >
                {q}
              </blockquote>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
