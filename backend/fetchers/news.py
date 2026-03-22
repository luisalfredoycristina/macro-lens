"""
GDELT news fetcher — free, no API key required.
Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# Country → search query mapping
COUNTRY_QUERIES: dict[str, str] = {
    "USA": "United States economy federal reserve inflation trade",
    "CHN": "China economy PBOC trade tariffs",
    "DEU": "Germany economy ECB Eurozone",
    "JPN": "Japan economy Bank of Japan yen",
    "GBR": "United Kingdom Bank of England economy",
    "FRA": "France economy ECB",
    "CAN": "Canada economy Bank of Canada",
    "AUS": "Australia economy Reserve Bank",
    "BRA": "Brazil economy Banco Central",
    "IND": "India economy RBI rupee",
    "MEX": "Mexico economy peso trade",
    "KOR": "South Korea economy Bank of Korea",
    "TUR": "Turkey economy inflation lira",
    "SAU": "Saudi Arabia OPEC oil economy",
    "ZAF": "South Africa economy rand",
    "SGP": "Singapore economy monetary policy",
    "VNM": "Vietnam economy trade exports",
    "IDN": "Indonesia economy Bank Indonesia",
    "ARG": "Argentina economy inflation peso",
    "POL": "Poland economy NBP zloty",
}

# Keywords for simple rule-based sentiment
_POSITIVE = {
    "growth", "surge", "rally", "beat", "strong", "recovery", "expansion",
    "soar", "gain", "rebound", "record", "robust", "accelerate", "outperform",
}
_NEGATIVE = {
    "recession", "crisis", "decline", "fall", "weak", "contraction",
    "slump", "plunge", "default", "risk", "slowdown", "downturn", "concern",
    "collapse", "warning", "miss",
}
_HAWKISH = {
    "hike", "tighten", "rate increase", "inflation", "overheating",
    "restrictive", "hawkish", "above target",
}
_DOVISH = {
    "cut", "ease", "easing", "stimulus", "accommodative", "dovish",
    "rate cut", "below target", "support",
}


def _score(title: str, desc: str = "") -> dict:
    """Keyword-based sentiment — returns tone, 0-100 score, hawkish, dovish flags."""
    text = (title + " " + desc).lower()
    pos = sum(1 for k in _POSITIVE if k in text)
    neg = sum(1 for k in _NEGATIVE if k in text)
    hawkish = any(k in text for k in _HAWKISH)
    dovish = any(k in text for k in _DOVISH)

    if pos + neg == 0:
        tone, score = "neutral", 50
    elif pos > neg:
        tone = "positive"
        score = min(50 + (pos - neg) * 12, 92)
    else:
        tone = "negative"
        score = max(50 - (neg - pos) * 12, 8)

    return {"tone": tone, "score": round(score), "hawkish": hawkish, "dovish": dovish}


async def fetch_country_news(country_code: str, n: int = 6) -> list[dict]:
    """Fetch latest English-language economic news for a country via GDELT."""
    query = COUNTRY_QUERIES.get(country_code, country_code)
    params = {
        "query": f"{query} sourcelang:english",
        "mode": "artlist",
        "maxrecords": n,
        "format": "json",
        "timespan": "5d",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(GDELT_BASE, params=params)
            if resp.status_code != 200:
                return []
            articles = resp.json().get("articles", [])
            result = []
            for art in articles[:n]:
                title = art.get("title", "").strip()
                if not title:
                    continue
                seendate = art.get("seendate", "")  # YYYYMMDDTHHMMSSZ
                date_str = (
                    f"{seendate[:4]}-{seendate[4:6]}-{seendate[6:8]}"
                    if len(seendate) >= 8
                    else ""
                )
                s = _score(title)
                result.append({
                    "title": title,
                    "url": art.get("url", ""),
                    "source": art.get("domain", ""),
                    "date": date_str,
                    "tone": s["tone"],
                    "sentiment_score": s["score"],
                    "hawkish": s["hawkish"],
                    "dovish": s["dovish"],
                })
            return result
    except Exception as exc:
        logger.warning(f"GDELT fetch failed for {country_code}: {exc}")
        return []


async def fetch_multi_country_news(country_codes: list[str], n_each: int = 5) -> dict[str, list[dict]]:
    """Fetch news for multiple countries concurrently."""
    tasks = [fetch_country_news(cc, n_each) for cc in country_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        cc: (res if isinstance(res, list) else [])
        for cc, res in zip(country_codes, results)
    }
