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
from datetime import date, timedelta
from typing import Optional
import logging

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
    allow_origins=["http://localhost:3000", "https://*.vercel.app", "https://*.app.github.dev"],
    allow_credentials=True,
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
