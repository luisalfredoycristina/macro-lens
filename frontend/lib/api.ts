const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status} ${path}`);
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface RegimeData {
  quadrant: "GOLDILOCKS" | "REFLATION" | "STAGFLATION" | "DEFLATION";
  description: string;
  color: "teal" | "amber" | "coral" | "purple";
  indicators: {
    gdp_growing: boolean;
    gdp_qoq_pct: number | null;
    cpi_yoy_pct: number | null;
    high_inflation: boolean;
    sahm_rule: number | null;
    yield_curve_spread: number | null;
    pce_latest: number | null;
    fed_funds: number | null;
  };
}

export interface Indicator {
  series_id: string;
  name: string;
  frequency: string;
  latest: number | null;
  prior: number | null;
  delta: number | null;
  delta_pct: number | null;
  trend: "up" | "down" | "flat";
}

export interface YieldPoint {
  tenor: string;
  yield: number | null;
}

export interface YieldCurveData {
  current: YieldPoint[];
  prior_3m: YieldPoint[];
}

export interface Country {
  iso3: string;
  name: string;
  exports_pct_gdp: number | null;
  current_account_pct_gdp: number | null;
  reserves_usd: number | null;
  external_debt_pct_gni: number | null;
  gdp_growth_pct: number | null;
  vulnerability_score: number;
  vulnerability_tier: "HIGH" | "MEDIUM" | "LOW";
}

export interface MacroSignal {
  id: number;
  signal_name: string;
  direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  conviction: number;
  trade_implication: string;
  fired_at: string;
  data_snapshot: Record<string, unknown>;
}

export interface Commodity {
  series_id: string;
  name: string;
  unit: string;
  latest: number | null;
  chg_1m_pct: number | null;
  chg_3m_pct: number | null;
}

// ── API functions ──────────────────────────────────────────────────────────

export const api = {
  regime: () => fetcher<RegimeData>("/api/regime"),
  indicators: () => fetcher<{ indicators: Indicator[] }>("/api/indicators"),
  yieldCurve: () => fetcher<YieldCurveData>("/api/yield-curve"),
  series: (id: string, periods = 60) =>
    fetcher<{ series_id: string; data: { date: string; value: number }[] }>(
      `/api/series/${id}?periods=${periods}`
    ),
  countries: () => fetcher<{ countries: Country[] }>("/api/countries"),
  signals: (limit = 20) => fetcher<{ signals: MacroSignal[] }>(`/api/signals?limit=${limit}`),
  commodities: () => fetcher<{ commodities: Commodity[] }>("/api/commodities"),
  health: () => fetcher<{ status: string; total_series_rows: number; last_fetch: string }>("/api/health"),
};
