"""
FRED API fetcher.
Docs: https://fred.stlouisfed.org/docs/api/fred/
Free key: https://fred.stlouisfed.org/docs/api/api_key.html
Rate limit: 120 requests/minute on free tier.
"""
import httpx
import asyncio
import os
import logging
from datetime import date, datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from ..db.models import MacroSeries

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# All FRED series to fetch. Format: (series_id, description)
FRED_SERIES = [
    # Growth
    ("GDPC1",              "Real GDP (SAAR, quarterly)"),
    # Inflation
    ("CPIAUCSL",           "CPI All Urban (monthly)"),
    ("PCEPI",              "PCE Price Index (monthly)"),
    ("PPIACO",             "PPI All Commodities (monthly)"),
    ("T10YIE",             "10Y Breakeven Inflation (daily)"),
    # Labour
    ("UNRATE",             "Unemployment Rate (monthly)"),
    ("SAHMREALTIME",       "Sahm Rule Real-Time (monthly)"),
    ("CES0500000003",      "Avg Hourly Earnings (monthly)"),
    # Rates & curve
    ("FEDFUNDS",           "Fed Funds Rate (monthly)"),
    ("T10Y2Y",             "10Y-2Y Treasury Spread (daily)"),
    ("DGS3MO",             "3-Month Treasury Yield (daily)"),
    ("DGS2",               "2-Year Treasury Yield (daily)"),
    ("DGS5",               "5-Year Treasury Yield (daily)"),
    ("DGS10",              "10-Year Treasury Yield (daily)"),
    ("DGS30",              "30-Year Treasury Yield (daily)"),
    # Commodities & money
    ("GOLDAMGBD228NLBM",   "Gold Price USD/troy oz (daily)"),
    ("DCOILWTICO",         "WTI Crude Oil Price (daily)"),
    ("M2SL",               "M2 Money Supply (monthly)"),
    # CPI components (for inflation nowcast)
    ("CPILFESL",           "Core CPI (less food and energy, monthly)"),
    ("CPIFABSL",           "CPI Food and Beverages (monthly)"),
    ("CPIUFDSL",           "CPI Food at Home (monthly)"),
    ("CPIENGSL",           "CPI Energy (monthly)"),
    ("CPIAPPSL",           "CPI Apparel (monthly)"),
    ("CPIMEDSL",           "CPI Medical Care Services (monthly)"),
    ("CUSR0000SAS4",       "CPI Shelter (monthly)"),
    ("CUSR0000SETA01",     "CPI New Vehicles (monthly)"),
    ("CUSR0000SETA02",     "CPI Used Cars and Trucks (monthly)"),
    ("CUSR0000SETB01",     "CPI Motor Fuel (monthly)"),
    ("CUSR0000SEHA",       "CPI Rent of Primary Residence (monthly)"),
]

async def fetch_series(client: httpx.AsyncClient, series_id: str, api_key: str,
                       observation_start: str = "2015-01-01") -> list[dict]:
    """Fetch observations for a single FRED series. Returns list of {date, value}."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
        "sort_order": "asc",
    }
    try:
        resp = await client.get(FRED_BASE, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        observations = []
        for obs in data.get("observations", []):
            val_str = obs.get("value", ".")
            if val_str == ".":
                continue
            try:
                observations.append({
                    "date": date.fromisoformat(obs["date"]),
                    "value": float(val_str),
                })
            except (ValueError, KeyError):
                continue
        return observations
    except Exception as e:
        logger.error(f"FRED fetch failed for {series_id}: {e}")
        return []


async def upsert_series(db: AsyncSession, series_id: str, observations: list[dict]):
    """Upsert observations into macro_series table in batches to avoid PostgreSQL parameter limits."""
    if not observations:
        return
    all_rows = [
        {
            "series_id": series_id,
            "country_code": "USA",
            "observation_date": obs["date"],
            "value": obs["value"],
            "source": "FRED",
            "fetched_at": datetime.utcnow(),
        }
        for obs in observations
    ]
    # PostgreSQL max params = 32767; each row uses 7 params → safe batch = 4000 rows
    batch_size = 4000
    for i in range(0, len(all_rows), batch_size):
        rows = all_rows[i:i + batch_size]
        stmt = insert(MacroSeries).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["series_id", "country_code", "observation_date"],
            set_={"value": stmt.excluded.value, "fetched_at": stmt.excluded.fetched_at}
        )
        await db.execute(stmt)
    await db.commit()


async def run_fred_fetcher(db: AsyncSession, full_backfill: bool = False):
    """Main entry point. Fetches all FRED series and upserts to DB."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY environment variable not set. "
                         "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html")

    observation_start = "2000-01-01" if full_backfill else "2020-01-01"
    logger.info(f"Starting FRED fetch for {len(FRED_SERIES)} series (start={observation_start})")

    async with httpx.AsyncClient() as client:
        for series_id, description in FRED_SERIES:
            logger.info(f"  Fetching {series_id} — {description}")
            observations = await fetch_series(client, series_id, api_key, observation_start)
            await upsert_series(db, series_id, observations)
            logger.info(f"    -> {len(observations)} observations upserted")
            await asyncio.sleep(0.6)  # stay well under 120 req/min rate limit

    logger.info("FRED fetch complete")
