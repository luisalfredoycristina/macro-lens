"""
World Bank Indicators API fetcher.
No API key required.
Endpoint: https://api.worldbank.org/v2/
Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""
import httpx
import asyncio
import logging
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from ..db.models import MacroSeries

logger = logging.getLogger(__name__)

WB_BASE = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"

# Indicators to fetch. Format: (indicator_code, description)
WB_INDICATORS = [
    ("NE.EXP.GNFS.ZS",      "Exports % of GDP"),
    ("BN.CAB.XOKA.GD.ZS",   "Current Account % of GDP"),
    ("BX.KLT.DINV.WD.GD.ZS","FDI net inflows % of GDP"),
    ("FI.RES.TOTL.CD",       "Total Reserves USD"),
    ("DT.DOD.DECT.GN.ZS",   "External Debt % of GNI"),
    ("NY.GDP.MKTP.KD.ZG",   "GDP Growth Rate annual %"),
    ("FP.CPI.TOTL.ZG",      "Inflation CPI annual %"),
    ("PA.NUS.FCRF",          "Official Exchange Rate LCU/USD"),
]

# 30 key countries: G7 + major EMs + commodity exporters + trade-war-exposed
COUNTRIES = [
    "USA", "GBR", "DEU", "FRA", "JPN", "CAN", "ITA",  # G7
    "CHN", "IND", "BRA", "MEX", "ZAF", "IDN", "TUR",  # Major EMs
    "KOR", "VNM", "THA", "SGP", "MYS", "PHL",          # Asia export-exposed
    "AUS", "NZL", "NOR", "SAU", "ARE",                  # Commodity/energy
    "EGY", "NGA", "ARG", "POL", "SWE",                  # Other EM / Europe
]


async def fetch_wb_indicator(client: httpx.AsyncClient, country: str,
                              indicator: str, date_range: str = "2010:2024") -> list[dict]:
    """Fetch a single World Bank indicator for a single country."""
    url = WB_BASE.format(country=country, indicator=indicator)
    params = {"format": "json", "per_page": 100, "date": date_range}
    try:
        resp = await client.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2:
            return []
        results = []
        for item in payload[1] or []:
            if item.get("value") is None:
                continue
            try:
                year = int(item["date"])
                results.append({
                    "date": date(year, 12, 31),  # World Bank annual = end of year
                    "value": float(item["value"]),
                })
            except (ValueError, TypeError, KeyError):
                continue
        return results
    except Exception as e:
        logger.warning(f"WB fetch failed {country}/{indicator}: {e}")
        return []


async def upsert_wb_series(db: AsyncSession, indicator: str, country: str,
                            observations: list[dict]):
    if not observations:
        return
    rows = [
        {
            "series_id": indicator,
            "country_code": country,
            "observation_date": obs["date"],
            "value": obs["value"],
            "source": "WORLDBANK",
            "fetched_at": datetime.utcnow(),
        }
        for obs in observations
    ]
    stmt = insert(MacroSeries).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["series_id", "country_code", "observation_date"],
        set_={"value": stmt.excluded.value, "fetched_at": stmt.excluded.fetched_at}
    )
    await db.execute(stmt)
    await db.commit()


async def run_worldbank_fetcher(db: AsyncSession):
    """Fetch all indicators for all countries."""
    logger.info(f"Starting World Bank fetch: {len(WB_INDICATORS)} indicators × {len(COUNTRIES)} countries")
    async with httpx.AsyncClient() as client:
        for indicator_code, description in WB_INDICATORS:
            logger.info(f"  Indicator: {indicator_code} — {description}")
            for country in COUNTRIES:
                observations = await fetch_wb_indicator(client, country, indicator_code)
                await upsert_wb_series(db, indicator_code, country, observations)
                await asyncio.sleep(0.3)  # polite rate limiting
            logger.info(f"    -> Done for all countries")
    logger.info("World Bank fetch complete")
