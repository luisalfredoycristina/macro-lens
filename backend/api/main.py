"""
FastAPI application.
All endpoints read from PostgreSQL — never calls external APIs directly.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, text
from sqlalchemy.dialects.postgresql import insert
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Optional
import logging
import httpx
import asyncio
import re

from ..db.database import get_db, init_db
from ..db.models import MacroSeries, Signal, AlertConfig

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Macro Lens API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_latest(db: AsyncSession, series_id: str, country: str = "USA") -> float | None:
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == series_id)
        .where(MacroSeries.country_code == country)
        .where(MacroSeries.value.isnot(None))
        .order_by(desc(MacroSeries.observation_date))
        .limit(1)
    )
    val = result.scalar_one_or_none()
    return float(val) if val is not None else None


async def get_recent(db: AsyncSession, series_id: str, n: int = 13,
                      country: str = "USA") -> list[float]:
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == series_id)
        .where(MacroSeries.country_code == country)
        .where(MacroSeries.value.isnot(None))
        .order_by(desc(MacroSeries.observation_date))
        .limit(n)
    )
    return [float(r) for r in result.scalars().all()]


@app.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count()).select_from(MacroSeries))
    total_rows = result.scalar()
    result2 = await db.execute(
        select(MacroSeries.fetched_at).order_by(desc(MacroSeries.fetched_at)).limit(1)
    )
    last_fetch = result2.scalar_one_or_none()
    return {"status": "ok", "total_series_rows": total_rows, "last_fetch": last_fetch}


@app.get("/api/regime")
async def get_regime(db: AsyncSession = Depends(get_db)):
    """
    Returns current macro regime quadrant based on:
    - Growth: GDP QoQ momentum (positive = growing, negative = contracting)
    - Inflation: CPI YoY (above/below 2.5% target)
    Quadrants: GOLDILOCKS | REFLATION | STAGFLATION | DEFLATION
    """
    gdp_vals = await get_recent(db, "GDPC1", n=3)
    cpi_vals = await get_recent(db, "CPIAUCSL", n=13)
    sahm = await get_latest(db, "SAHMREALTIME")
    spread = await get_latest(db, "T10Y2Y")
    pce = await get_latest(db, "PCEPI")
    fedfunds = await get_latest(db, "FEDFUNDS")

    # Growth momentum
    gdp_growing = len(gdp_vals) >= 2 and gdp_vals[0] > gdp_vals[1]
    gdp_qoq = None
    if len(gdp_vals) >= 2 and gdp_vals[1]:
        gdp_qoq = round(((gdp_vals[0] - gdp_vals[1]) / abs(gdp_vals[1])) * 100, 2)

    # Inflation
    cpi_yoy = None
    if len(cpi_vals) >= 13 and cpi_vals[12]:
        cpi_yoy = round(((cpi_vals[0] - cpi_vals[12]) / abs(cpi_vals[12])) * 100, 2)
    high_inflation = cpi_yoy is not None and cpi_yoy > 2.5

    # Determine quadrant
    if gdp_growing and not high_inflation:
        quadrant = "GOLDILOCKS"
        description = "Growth expanding, inflation contained. Risk-on environment."
        color = "teal"
    elif gdp_growing and high_inflation:
        quadrant = "REFLATION"
        description = "Growth and inflation rising together. Commodities, short duration."
        color = "amber"
    elif not gdp_growing and high_inflation:
        quadrant = "STAGFLATION"
        description = "Growth stalling, inflation elevated. Most challenging regime."
        color = "coral"
    else:
        quadrant = "DEFLATION"
        description = "Growth contracting, inflation falling. Long duration, safe havens."
        color = "purple"

    return {
        "quadrant": quadrant,
        "description": description,
        "color": color,
        "indicators": {
            "gdp_growing": gdp_growing,
            "gdp_qoq_pct": gdp_qoq,
            "cpi_yoy_pct": cpi_yoy,
            "high_inflation": high_inflation,
            "sahm_rule": sahm,
            "yield_curve_spread": spread,
            "pce_latest": pce,
            "fed_funds": fedfunds,
        }
    }


@app.get("/api/indicators")
async def get_indicators(db: AsyncSession = Depends(get_db)):
    """Latest reading + delta for all tracked FRED series."""
    series_list = [
        ("GDPC1", "Real GDP", "quarterly"),
        ("CPIAUCSL", "CPI", "monthly"),
        ("PCEPI", "PCE Deflator", "monthly"),
        ("PPIACO", "PPI", "monthly"),
        ("UNRATE", "Unemployment Rate", "monthly"),
        ("SAHMREALTIME", "Sahm Rule", "monthly"),
        ("FEDFUNDS", "Fed Funds Rate", "monthly"),
        ("T10Y2Y", "Yield Curve (10Y-2Y)", "daily"),
        ("T10YIE", "10Y Breakeven Inflation", "daily"),
        ("GOLDAMGBD228NLBM", "Gold Price", "daily"),
        ("DCOILWTICO", "WTI Crude Oil", "daily"),
        ("M2SL", "M2 Money Supply", "monthly"),
        ("CES0500000003", "Avg Hourly Earnings", "monthly"),
    ]
    indicators = []
    for series_id, name, frequency in series_list:
        vals = await get_recent(db, series_id, n=2)
        latest = vals[0] if vals else None
        prior = vals[1] if len(vals) > 1 else None
        delta = None
        delta_pct = None
        if latest is not None and prior is not None and prior != 0:
            delta = round(latest - prior, 4)
            delta_pct = round(((latest - prior) / abs(prior)) * 100, 3)
        indicators.append({
            "series_id": series_id,
            "name": name,
            "frequency": frequency,
            "latest": latest,
            "prior": prior,
            "delta": delta,
            "delta_pct": delta_pct,
            "trend": "up" if delta and delta > 0 else ("down" if delta and delta < 0 else "flat"),
        })
    return {"indicators": indicators}


@app.get("/api/series/{series_id}")
async def get_series_history(series_id: str, periods: int = 60,
                              db: AsyncSession = Depends(get_db)):
    """Time-series history for charting."""
    result = await db.execute(
        select(MacroSeries.observation_date, MacroSeries.value)
        .where(MacroSeries.series_id == series_id)
        .where(MacroSeries.country_code == "USA")
        .where(MacroSeries.value.isnot(None))
        .order_by(desc(MacroSeries.observation_date))
        .limit(periods)
    )
    rows = result.all()
    return {
        "series_id": series_id,
        "data": [{"date": str(r[0]), "value": float(r[1])} for r in reversed(rows)]
    }


@app.get("/api/yield-curve")
async def get_yield_curve(db: AsyncSession = Depends(get_db)):
    """Current and historical yield curve snapshots."""
    tenors = [("DGS3MO", "3M"), ("DGS2", "2Y"), ("DGS5", "5Y"), ("DGS10", "10Y"), ("DGS30", "30Y")]
    current = []
    for series_id, label in tenors:
        val = await get_latest(db, series_id)
        current.append({"tenor": label, "yield": val})

    # 3 months ago snapshot
    three_months_ago = date.today() - timedelta(days=90)
    prior = []
    for series_id, label in tenors:
        result = await db.execute(
            select(MacroSeries.value)
            .where(MacroSeries.series_id == series_id)
            .where(MacroSeries.country_code == "USA")
            .where(MacroSeries.observation_date <= three_months_ago)
            .where(MacroSeries.value.isnot(None))
            .order_by(desc(MacroSeries.observation_date))
            .limit(1)
        )
        val = result.scalar_one_or_none()
        prior.append({"tenor": label, "yield": float(val) if val else None})

    return {"current": current, "prior_3m": prior}


@app.get("/api/countries")
async def get_countries(db: AsyncSession = Depends(get_db)):
    """
    World Bank country exposure table.
    Returns exports/GDP, current account, reserves, external debt per country.
    Computes a vulnerability score (0-100) for tariff/war shock exposure.
    """
    countries_meta = {
        "USA": "United States", "GBR": "United Kingdom", "DEU": "Germany",
        "FRA": "France", "JPN": "Japan", "CAN": "Canada", "ITA": "Italy",
        "CHN": "China", "IND": "India", "BRA": "Brazil", "MEX": "Mexico",
        "ZAF": "South Africa", "IDN": "Indonesia", "TUR": "Turkey",
        "KOR": "South Korea", "VNM": "Vietnam", "THA": "Thailand",
        "SGP": "Singapore", "MYS": "Malaysia", "PHL": "Philippines",
        "AUS": "Australia", "NZL": "New Zealand", "NOR": "Norway",
        "SAU": "Saudi Arabia", "ARE": "UAE", "EGY": "Egypt",
        "NGA": "Nigeria", "ARG": "Argentina", "POL": "Poland", "SWE": "Sweden",
    }

    result = await db.execute(
        select(
            MacroSeries.country_code,
            MacroSeries.series_id,
            MacroSeries.value,
        )
        .where(MacroSeries.source == "WORLDBANK")
        .where(MacroSeries.series_id.in_([
            "NE.EXP.GNFS.ZS", "BN.CAB.XOKA.GD.ZS",
            "FI.RES.TOTL.CD", "DT.DOD.DECT.GN.ZS", "NY.GDP.MKTP.KD.ZG"
        ]))
        .where(MacroSeries.observation_date >= date(2020, 1, 1))
        .order_by(MacroSeries.country_code, MacroSeries.series_id, desc(MacroSeries.observation_date))
    )
    rows = result.all()

    # Group latest value per (country, indicator)
    latest: dict[tuple, float] = {}
    for country_code, series_id, value in rows:
        key = (country_code, series_id)
        if key not in latest and value is not None:
            latest[key] = float(value)

    countries = []
    for iso3, name in countries_meta.items():
        exports_gdp = latest.get((iso3, "NE.EXP.GNFS.ZS"))
        current_account = latest.get((iso3, "BN.CAB.XOKA.GD.ZS"))
        reserves = latest.get((iso3, "FI.RES.TOTL.CD"))
        ext_debt = latest.get((iso3, "DT.DOD.DECT.GN.ZS"))
        gdp_growth = latest.get((iso3, "NY.GDP.MKTP.KD.ZG"))

        # Vulnerability score: high exports/GDP + high ext debt + low reserves = more vulnerable
        score = 0
        if exports_gdp: score += min(exports_gdp / 100 * 40, 40)  # 0-40 pts
        if ext_debt: score += min(ext_debt / 200 * 30, 30)         # 0-30 pts
        if current_account and current_account < 0: score += 20    # deficit = +20
        if gdp_growth and gdp_growth < 1: score += 10              # slow growth = +10
        score = round(min(score, 100))

        tier = "HIGH" if score >= 60 else ("MEDIUM" if score >= 30 else "LOW")

        countries.append({
            "iso3": iso3,
            "name": name,
            "exports_pct_gdp": exports_gdp,
            "current_account_pct_gdp": current_account,
            "reserves_usd": reserves,
            "external_debt_pct_gni": ext_debt,
            "gdp_growth_pct": gdp_growth,
            "vulnerability_score": score,
            "vulnerability_tier": tier,
        })

    countries.sort(key=lambda x: x["vulnerability_score"], reverse=True)
    return {"countries": countries}


@app.get("/api/signals")
async def get_signals(active_only: bool = False, limit: int = 50,
                       db: AsyncSession = Depends(get_db)):
    """List fired signals, newest first."""
    query = select(Signal).order_by(desc(Signal.fired_at)).limit(limit)
    if active_only:
        query = query.where(Signal.alert_sent == False)
    result = await db.execute(query)
    signals = result.scalars().all()
    return {
        "signals": [
            {
                "id": s.id,
                "signal_name": s.signal_name,
                "direction": s.direction,
                "conviction": s.conviction,
                "trade_implication": s.trade_implication,
                "fired_at": str(s.fired_at),
                "data_snapshot": s.data_snapshot,
            }
            for s in signals
        ]
    }


@app.get("/api/commodities")
async def get_commodities(db: AsyncSession = Depends(get_db)):
    """Commodity prices with % change windows."""
    commodities = [
        ("GOLDAMGBD228NLBM", "Gold", "USD/oz"),
        ("DCOILWTICO", "WTI Crude", "USD/bbl"),
    ]
    result_list = []
    for series_id, name, unit in commodities:
        now_val = await get_latest(db, series_id)
        vals_30d = await get_recent(db, series_id, n=22)
        vals_90d = await get_recent(db, series_id, n=66)

        def pct_chg(current, prior_list):
            if not prior_list or current is None: return None
            prior = prior_list[-1]
            if prior == 0: return None
            return round(((current - prior) / abs(prior)) * 100, 2)

        result_list.append({
            "series_id": series_id,
            "name": name,
            "unit": unit,
            "latest": now_val,
            "chg_1m_pct": pct_chg(now_val, vals_30d),
            "chg_3m_pct": pct_chg(now_val, vals_90d),
        })
    return {"commodities": result_list}


@app.post("/api/run-fetch")
async def trigger_fetch(db: AsyncSession = Depends(get_db)):
    """Manual trigger for data fetch + signal evaluation. For dev/testing."""
    from ..fetchers.fred import run_fred_fetcher
    from ..fetchers.worldbank import run_worldbank_fetcher
    from ..signals.engine import run_signal_engine
    from ..alerts.dispatcher import dispatch_pending_alerts

    await run_fred_fetcher(db)
    await run_worldbank_fetcher(db)
    fired = await run_signal_engine(db)
    await dispatch_pending_alerts(db)
    return {"status": "complete", "signals_fired": len(fired)}


# ── News feed ─────────────────────────────────────────────────────────────────

@app.get("/api/news")
async def get_news(countries: str = "USA,CHN,DEU,JPN,GBR,BRA,IND,MEX,KOR,TUR"):
    """
    Fetch economic news per country from GDELT (free, no key needed).
    countries: comma-separated ISO3 codes
    """
    from ..fetchers.news import fetch_multi_country_news
    codes = [c.strip().upper() for c in countries.split(",") if c.strip()]
    news_map = await fetch_multi_country_news(codes, n_each=5)

    # Aggregate overall sentiment per country
    result = {}
    for cc, articles in news_map.items():
        if not articles:
            result[cc] = {"articles": [], "avg_sentiment": 50, "dominant_tone": "neutral"}
            continue
        avg = round(sum(a["sentiment_score"] for a in articles) / len(articles))
        tones = [a["tone"] for a in articles]
        dominant = max(set(tones), key=tones.count)
        result[cc] = {
            "articles": articles,
            "avg_sentiment": avg,
            "dominant_tone": dominant,
        }

    return {"news": result}


# ── Inflation nowcast ─────────────────────────────────────────────────────────

_CPI_COMPONENTS = [
    ("CPIAUCSL",       "Headline CPI",          "total"),
    ("CPILFESL",       "Core CPI",              "core"),
    ("CPIFABSL",       "Food & Beverages",      "food"),
    ("CPIUFDSL",       "Food at Home",          "food"),
    ("CPIENGSL",       "Energy",                "energy"),
    ("CUSR0000SETB01", "Motor Fuel",            "energy"),
    ("CPIAPPSL",       "Apparel",               "goods"),
    ("CUSR0000SETA01", "New Vehicles",          "goods"),
    ("CUSR0000SETA02", "Used Vehicles",         "goods"),
    ("CUSR0000SAS4",   "Shelter",               "services"),
    ("CUSR0000SEHA",   "Primary Rent",          "services"),
    ("CPIMEDSL",       "Medical Care",          "services"),
]


@app.get("/api/inflation-nowcast")
async def get_inflation_nowcast(db: AsyncSession = Depends(get_db)):
    """
    YoY % change for each CPI component — builds the inflation nowcast chart.
    Uses 13 observations (12 months) to compute year-over-year change.
    """
    components = []
    for series_id, label, category in _CPI_COMPONENTS:
        vals = await get_recent(db, series_id, n=14)
        if len(vals) < 13:
            components.append({
                "series_id": series_id,
                "label": label,
                "category": category,
                "yoy_pct": None,
                "mom_pct": None,
                "latest": None,
            })
            continue

        latest_val = vals[0]
        year_ago_val = vals[12]
        prior_val = vals[1]

        yoy = round(((latest_val - year_ago_val) / abs(year_ago_val)) * 100, 2) if year_ago_val else None
        mom = round(((latest_val - prior_val) / abs(prior_val)) * 100, 2) if prior_val else None

        components.append({
            "series_id": series_id,
            "label": label,
            "category": category,
            "yoy_pct": yoy,
            "mom_pct": mom,
            "latest": round(latest_val, 3),
        })

    # Sort by absolute YoY (biggest movers first), with Nones at end
    components.sort(
        key=lambda x: abs(x["yoy_pct"]) if x["yoy_pct"] is not None else -1,
        reverse=True,
    )

    # Compute category aggregates
    categories: dict[str, list[float]] = {}
    for c in components:
        if c["yoy_pct"] is not None:
            categories.setdefault(c["category"], []).append(c["yoy_pct"])
    cat_summary = {
        cat: round(sum(vals) / len(vals), 2)
        for cat, vals in categories.items()
    }

    return {
        "components": components,
        "category_summary": cat_summary,
        "as_of": str(date.today()),
    }


# ── Macro events calendar ─────────────────────────────────────────────────────

def _build_events_calendar() -> list[dict]:
    """
    Return upcoming (and recent) macro events.
    Events are computed/hardcoded based on known 2026 schedule.
    """
    today = date.today()
    events = []

    # FOMC meetings 2026 (decision day = second day)
    fomc_dates_2026 = [
        date(2026, 1, 29), date(2026, 3, 19), date(2026, 5, 7),
        date(2026, 6, 18), date(2026, 7, 30), date(2026, 9, 17),
        date(2026, 10, 29), date(2026, 12, 10),
    ]
    for d in fomc_dates_2026:
        events.append({
            "date": str(d),
            "event": "FOMC Rate Decision",
            "category": "central_bank",
            "importance": "high",
            "description": "Federal Reserve interest rate decision and statement.",
            "days_away": (d - today).days,
        })

    # Non-Farm Payrolls 2026 — first Friday of each month
    nfp_2026 = [
        date(2026, 1, 2), date(2026, 2, 6), date(2026, 3, 6),
        date(2026, 4, 3), date(2026, 5, 1), date(2026, 6, 5),
        date(2026, 7, 2), date(2026, 8, 7), date(2026, 9, 4),
        date(2026, 10, 2), date(2026, 11, 6), date(2026, 12, 4),
    ]
    for d in nfp_2026:
        events.append({
            "date": str(d),
            "event": "Non-Farm Payrolls (BLS)",
            "category": "labor",
            "importance": "high",
            "description": "Monthly US employment situation report from the Bureau of Labor Statistics.",
            "days_away": (d - today).days,
        })

    # CPI releases 2026 (typically 2nd or 3rd Wednesday of following month)
    cpi_2026 = [
        date(2026, 1, 14), date(2026, 2, 11), date(2026, 3, 11),
        date(2026, 4, 10), date(2026, 5, 13), date(2026, 6, 10),
        date(2026, 7, 14), date(2026, 8, 12), date(2026, 9, 10),
        date(2026, 10, 14), date(2026, 11, 12), date(2026, 12, 10),
    ]
    for d in cpi_2026:
        events.append({
            "date": str(d),
            "event": "CPI Inflation Report (BLS)",
            "category": "inflation",
            "importance": "high",
            "description": "Consumer Price Index release — headline and core inflation readings.",
            "days_away": (d - today).days,
        })

    # GDP releases 2026 (advance estimate: last week of January, April, July, October)
    gdp_2026 = [
        (date(2026, 1, 29), "Q4 2025 GDP Advance"),
        (date(2026, 4, 29), "Q1 2026 GDP Advance"),
        (date(2026, 7, 29), "Q2 2026 GDP Advance"),
        (date(2026, 10, 28), "Q3 2026 GDP Advance"),
    ]
    for d, label in gdp_2026:
        events.append({
            "date": str(d),
            "event": f"GDP {label} (BEA)",
            "category": "growth",
            "importance": "high",
            "description": "Bureau of Economic Analysis advance estimate of GDP growth.",
            "days_away": (d - today).days,
        })

    # ECB meetings 2026
    ecb_2026 = [
        date(2026, 1, 30), date(2026, 3, 6), date(2026, 4, 30),
        date(2026, 6, 5), date(2026, 7, 24), date(2026, 9, 11),
        date(2026, 10, 30), date(2026, 12, 18),
    ]
    for d in ecb_2026:
        events.append({
            "date": str(d),
            "event": "ECB Rate Decision",
            "category": "central_bank",
            "importance": "medium",
            "description": "European Central Bank monetary policy decision.",
            "days_away": (d - today).days,
        })

    # Sort by date and filter to ±60 days from today
    events = [e for e in events if -30 <= e["days_away"] <= 90]
    events.sort(key=lambda x: x["days_away"])
    return events


@app.get("/api/events")
async def get_events():
    """Upcoming macro events calendar (FOMC, NFP, CPI, GDP, ECB)."""
    return {"events": _build_events_calendar()}


# ── FOMC minutes analysis ─────────────────────────────────────────────────────

_FOMC_DATES_2026 = [
    ("2026-01-29", "20260129"),
    ("2025-12-18", "20251218"),
    ("2025-11-07", "20251107"),
    ("2025-09-18", "20250918"),
    ("2025-07-30", "20250730"),
    ("2025-06-18", "20250618"),
    ("2025-05-07", "20250507"),
    ("2025-03-19", "20250319"),
    ("2025-01-29", "20250129"),
]

_HAWKISH_TERMS = [
    "inflation remain", "above target", "tighten", "restrictive",
    "overshoot", "elevated", "vigilant", "rate increase", "hike",
    "upside risk", "persistence", "further increases",
]
_DOVISH_TERMS = [
    "cut", "easing", "accommodative", "below target", "undershooting",
    "labor market slowing", "downside risk", "pause", "patient",
    "gradual", "reduce", "lower rate",
]
_NEUTRAL_TERMS = [
    "data dependent", "balanced", "appropriate", "monitor",
    "assess", "uncertainty", "flexible",
]


def _analyze_minutes_text(text: str) -> dict:
    """Extract policy signals from raw FOMC minutes HTML text."""
    text_lower = text.lower()

    hawkish_hits = [(t, text_lower.count(t)) for t in _HAWKISH_TERMS if t in text_lower]
    dovish_hits = [(t, text_lower.count(t)) for t in _DOVISH_TERMS if t in text_lower]
    neutral_hits = [(t, text_lower.count(t)) for t in _NEUTRAL_TERMS if t in text_lower]

    hawk_score = sum(c for _, c in hawkish_hits)
    dove_score = sum(c for _, c in dovish_hits)
    total = hawk_score + dove_score + 1
    stance_score = round((hawk_score / total) * 100)  # 0=fully dovish, 100=fully hawkish

    if stance_score >= 60:
        stance = "HAWKISH"
    elif stance_score <= 40:
        stance = "DOVISH"
    else:
        stance = "NEUTRAL"

    # Extract key paragraphs — look for policy-relevant sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    key_quotes = []
    for s in sentences:
        s = s.strip()
        s_lower = s.lower()
        if len(s) < 60 or len(s) > 400:
            continue
        if any(k in s_lower for k in ["inflation", "employment", "rate", "policy", "economic"]):
            # Clean up HTML artifacts
            s_clean = re.sub(r'\s+', ' ', s).strip()
            if s_clean and s_clean not in key_quotes:
                key_quotes.append(s_clean)
        if len(key_quotes) >= 6:
            break

    return {
        "stance": stance,
        "stance_score": stance_score,
        "hawkish_count": hawk_score,
        "dovish_count": dove_score,
        "hawkish_terms_found": [t for t, _ in hawkish_hits[:5]],
        "dovish_terms_found": [t for t, _ in dovish_hits[:5]],
        "key_quotes": key_quotes,
    }


@app.get("/api/fomc")
async def get_fomc_analysis(db: AsyncSession = Depends(get_db)):
    """
    Fetch and analyze the latest available FOMC meeting minutes.
    Returns policy stance analysis + current macro context from DB.
    """
    minutes_text = ""
    meeting_date = ""
    minutes_url = ""

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for meet_date, date_code in _FOMC_DATES_2026:
            url = f"https://www.federalreserve.gov/monetarypolicy/fomcminutes{date_code}.htm"
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.text) > 5000:
                    # Strip HTML tags
                    raw = re.sub(r'<[^>]+>', ' ', resp.text)
                    raw = re.sub(r'&[a-z]+;', ' ', raw)
                    raw = re.sub(r'\s+', ' ', raw)
                    minutes_text = raw.strip()
                    meeting_date = meet_date
                    minutes_url = url
                    break
            except Exception as exc:
                logger.warning(f"FOMC fetch failed for {date_code}: {exc}")
                continue

    analysis: dict = {}
    if minutes_text:
        analysis = _analyze_minutes_text(minutes_text)
    else:
        analysis = {
            "stance": "UNKNOWN",
            "stance_score": 50,
            "hawkish_count": 0,
            "dovish_count": 0,
            "hawkish_terms_found": [],
            "dovish_terms_found": [],
            "key_quotes": ["Could not fetch FOMC minutes. Check network connectivity."],
        }

    # Pull current macro context from DB
    fedfunds_vals = await get_recent(db, "FEDFUNDS", n=13)
    cpi_vals = await get_recent(db, "CPIAUCSL", n=13)
    core_vals = await get_recent(db, "CPILFESL", n=13)
    breakeven = await get_latest(db, "T10YIE")
    spread = await get_latest(db, "T10Y2Y")
    unrate = await get_latest(db, "UNRATE")
    sahm = await get_latest(db, "SAHMREALTIME")

    cpi_yoy = None
    if len(cpi_vals) >= 13 and cpi_vals[12]:
        cpi_yoy = round(((cpi_vals[0] - cpi_vals[12]) / abs(cpi_vals[12])) * 100, 2)
    core_yoy = None
    if len(core_vals) >= 13 and core_vals[12]:
        core_yoy = round(((core_vals[0] - core_vals[12]) / abs(core_vals[12])) * 100, 2)

    return {
        "meeting_date": meeting_date,
        "minutes_url": minutes_url,
        "analysis": analysis,
        "macro_context": {
            "fed_funds_rate": fedfunds_vals[0] if fedfunds_vals else None,
            "cpi_yoy_pct": cpi_yoy,
            "core_cpi_yoy_pct": core_yoy,
            "breakeven_inflation_10y": breakeven,
            "yield_curve_spread": spread,
            "unemployment_rate": unrate,
            "sahm_rule": sahm,
            "fed_funds_history": [
                {"value": v}
                for v in reversed(fedfunds_vals[:12])
            ],
        },
    }
