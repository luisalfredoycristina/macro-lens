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

// ── News ───────────────────────────────────────────────────────────────────

export interface NewsArticle {
  title: string;
  url: string;
  source: string;
  date: string;
  tone: "positive" | "negative" | "neutral";
  sentiment_score: number;
  hawkish: boolean;
  dovish: boolean;
}

export interface CountryNews {
  articles: NewsArticle[];
  avg_sentiment: number;
  dominant_tone: "positive" | "negative" | "neutral";
}

// ── Inflation nowcast ──────────────────────────────────────────────────────

export interface CpiComponent {
  series_id: string;
  label: string;
  category: "total" | "core" | "food" | "energy" | "goods" | "services";
  yoy_pct: number | null;
  mom_pct: number | null;
  latest: number | null;
}

export interface InflationNowcast {
  components: CpiComponent[];
  category_summary: Record<string, number>;
  as_of: string;
}

// ── Events ─────────────────────────────────────────────────────────────────

export interface MacroEvent {
  date: string;
  event: string;
  category: "central_bank" | "labor" | "inflation" | "growth";
  importance: "high" | "medium" | "low";
  description: string;
  days_away: number;
}

// ── FOMC ───────────────────────────────────────────────────────────────────

export interface FomcAnalysis {
  meeting_date: string;
  minutes_url: string;
  analysis: {
    stance: "HAWKISH" | "DOVISH" | "NEUTRAL" | "UNKNOWN";
    stance_score: number;
    hawkish_count: number;
    dovish_count: number;
    hawkish_terms_found: string[];
    dovish_terms_found: string[];
    key_quotes: string[];
  };
  macro_context: {
    fed_funds_rate: number | null;
    cpi_yoy_pct: number | null;
    core_cpi_yoy_pct: number | null;
    breakeven_inflation_10y: number | null;
    yield_curve_spread: number | null;
    unemployment_rate: number | null;
    sahm_rule: number | null;
    fed_funds_history: { value: number }[];
  };
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
  news: (countries = "USA,CHN,DEU,JPN,GBR,BRA,IND,MEX,KOR,TUR") =>
    fetcher<{ news: Record<string, CountryNews> }>(`/api/news?countries=${countries}`),
  inflationNowcast: () => fetcher<InflationNowcast>("/api/inflation-nowcast"),
  events: () => fetcher<{ events: MacroEvent[] }>("/api/events"),
  fomc: () => fetcher<FomcAnalysis>("/api/fomc"),
};
