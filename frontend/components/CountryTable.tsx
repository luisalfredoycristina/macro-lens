"use client";
import { useState } from "react";
import type { Country } from "../lib/api";
import clsx from "clsx";

interface Props {
  countries: Country[];
}

const TIER_STYLES = {
  HIGH:   "bg-red-100 text-red-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  LOW:    "bg-teal-100 text-teal-800",
};

function fmt(val: number | null, decimals = 1, suffix = "%"): string {
  if (val === null) return "—";
  return `${val.toFixed(decimals)}${suffix}`;
}

function fmtReserves(val: number | null): string {
  if (val === null) return "—";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(1)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(0)}B`;
  return `$${(val / 1e6).toFixed(0)}M`;
}

type SortKey = "vulnerability_score" | "exports_pct_gdp" | "external_debt_pct_gni" | "gdp_growth_pct";

export default function CountryTable({ countries }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("vulnerability_score");
  const [asc, setAsc] = useState(false);
  const [tierFilter, setTierFilter] = useState<string>("ALL");

  const sorted = [...countries]
    .filter((c) => tierFilter === "ALL" || c.vulnerability_tier === tierFilter)
    .sort((a, b) => {
      const av = a[sortKey] ?? -999, bv = b[sortKey] ?? -999;
      return asc ? av - bv : bv - av;
    });

  const toggle = (key: SortKey) => {
    if (sortKey === key) setAsc(!asc);
    else { setSortKey(key); setAsc(false); }
  };

  const TH = ({ label, sk }: { label: string; sk: SortKey }) => (
    <th
      className="px-3 py-2 text-left text-xs font-semibold text-gray-500 cursor-pointer hover:text-gray-900 whitespace-nowrap"
      onClick={() => toggle(sk)}
    >
      {label} {sortKey === sk ? (asc ? "▲" : "▼") : ""}
    </th>
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div>
          <h2 className="font-semibold text-gray-700">Country Risk Exposure</h2>
          <p className="text-xs text-gray-400 mt-0.5">World Bank data — tariff & war shock vulnerability</p>
        </div>
        <div className="flex gap-2">
          {["ALL", "HIGH", "MEDIUM", "LOW"].map((t) => (
            <button
              key={t}
              onClick={() => setTierFilter(t)}
              className={clsx(
                "text-xs px-3 py-1 rounded-full border transition-colors",
                tierFilter === t ? "bg-gray-900 text-white border-gray-900" : "border-gray-200 text-gray-500 hover:border-gray-400"
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Country</th>
              <TH label="Vulnerability" sk="vulnerability_score" />
              <TH label="Exports/GDP" sk="exports_pct_gdp" />
              <TH label="Ext. Debt/GNI" sk="external_debt_pct_gni" />
              <TH label="GDP Growth" sk="gdp_growth_pct" />
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">CA Balance</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Reserves</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {sorted.map((c) => (
              <tr key={c.iso3} className="hover:bg-gray-50 transition-colors">
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-400 w-8">{c.iso3}</span>
                    <span className="text-sm font-medium text-gray-900">{c.name}</span>
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={clsx("h-full rounded-full", c.vulnerability_tier === "HIGH" ? "bg-red-500" : c.vulnerability_tier === "MEDIUM" ? "bg-amber-500" : "bg-teal-500")}
                        style={{ width: `${c.vulnerability_score}%` }}
                      />
                    </div>
                    <span className={clsx("text-xs font-semibold px-1.5 py-0.5 rounded", TIER_STYLES[c.vulnerability_tier])}>
                      {c.vulnerability_tier}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2.5 text-sm text-gray-700">{fmt(c.exports_pct_gdp)}</td>
                <td className="px-3 py-2.5 text-sm text-gray-700">{fmt(c.external_debt_pct_gni)}</td>
                <td className="px-3 py-2.5 text-sm">
                  <span className={clsx(c.gdp_growth_pct != null && c.gdp_growth_pct > 0 ? "text-teal-700" : "text-red-700")}>
                    {fmt(c.gdp_growth_pct)}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-sm text-gray-700">
                  <span className={clsx(c.current_account_pct_gdp != null && c.current_account_pct_gdp >= 0 ? "text-teal-700" : "text-red-700")}>
                    {fmt(c.current_account_pct_gdp)}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-sm text-gray-700">{fmtReserves(c.reserves_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
