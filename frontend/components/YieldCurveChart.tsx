"use client";
import useSWR from "swr";
import { api } from "../lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function YieldCurveChart() {
  const { data } = useSWR("yield-curve", api.yieldCurve, { refreshInterval: 300_000 });

  if (!data) return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <h2 className="font-semibold text-gray-700 mb-4">US Treasury Yield Curve</h2>
      <div className="h-56 flex items-center justify-center text-gray-400 text-sm">Loading...</div>
    </div>
  );

  // Merge current and prior into a single array keyed by tenor
  const chartData = data.current.map((point, i) => ({
    tenor: point.tenor,
    current: point.yield,
    prior_3m: data.prior_3m[i]?.yield ?? null,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <h2 className="font-semibold text-gray-700 mb-1">US Treasury Yield Curve</h2>
      <p className="text-xs text-gray-400 mb-4">Current vs 3 months ago (%)</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="tenor" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
          <Tooltip formatter={(v: number) => `${v?.toFixed(2)}%`} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="current" stroke="#1D9E75" strokeWidth={2.5} dot={{ r: 3 }} name="Current" />
          <Line type="monotone" dataKey="prior_3m" stroke="#BA7517" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="3M Ago" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
