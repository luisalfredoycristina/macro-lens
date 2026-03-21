"""
Signal evaluation engine.
Loads all signals from registry, queries DB for required series,
evaluates conditions, writes new signals to DB if not in cooldown.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, text
from ..db.models import MacroSeries, Signal
from .registry import load_registry, SignalDefinition

logger = logging.getLogger(__name__)


async def get_latest_value(db: AsyncSession, series_id: str,
                            country_code: str = "USA") -> float | None:
    """Get the most recent non-null value for a series."""
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == series_id)
        .where(MacroSeries.country_code == country_code)
        .where(MacroSeries.value.isnot(None))
        .order_by(desc(MacroSeries.observation_date))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


async def get_recent_values(db: AsyncSession, series_id: str,
                             n: int = 5, country_code: str = "USA") -> list[float]:
    """Get the N most recent values for a series (newest first)."""
    result = await db.execute(
        select(MacroSeries.value)
        .where(MacroSeries.series_id == series_id)
        .where(MacroSeries.country_code == country_code)
        .where(MacroSeries.value.isnot(None))
        .order_by(desc(MacroSeries.observation_date))
        .limit(n)
    )
    return [float(r) for r in result.scalars().all()]


async def get_mom_change(db: AsyncSession, series_id: str) -> float | None:
    """Get month-over-month percentage change for a series."""
    vals = await get_recent_values(db, series_id, n=2)
    if len(vals) < 2 or vals[1] == 0:
        return None
    return ((vals[0] - vals[1]) / abs(vals[1])) * 100


async def get_yoy_change(db: AsyncSession, series_id: str,
                          country_code: str = "USA") -> float | None:
    """Get year-over-year percentage change."""
    vals = await get_recent_values(db, series_id, n=13, country_code=country_code)
    if len(vals) < 13 or vals[12] == 0:
        return None
    return ((vals[0] - vals[12]) / abs(vals[12])) * 100


async def is_in_cooldown(db: AsyncSession, signal_name: str,
                          cooldown_hours: int = 24) -> bool:
    """Return True if this signal fired within the cooldown window."""
    cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)
    result = await db.execute(
        select(Signal.id)
        .where(Signal.signal_name == signal_name)
        .where(Signal.fired_at >= cutoff)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def fire_signal(db: AsyncSession, signal: SignalDefinition,
                       snapshot: dict):
    """Write a fired signal to the DB."""
    new_signal = Signal(
        signal_name=signal.name,
        direction=signal.direction,
        conviction=signal.conviction,
        trade_implication=signal.trade_implication,
        data_snapshot=snapshot,
        alert_sent=False,
    )
    db.add(new_signal)
    await db.commit()
    await db.refresh(new_signal)
    logger.info(f"  SIGNAL FIRED: {signal.name} | {signal.direction} | conviction={signal.conviction}")
    return new_signal


async def evaluate_yield_curve_inversion(db: AsyncSession) -> tuple[bool, dict]:
    spread = await get_latest_value(db, "T10Y2Y")
    if spread is None:
        return False, {}
    recent = await get_recent_values(db, "T10Y2Y", n=5)
    inverted_count = sum(1 for v in recent if v < 0)
    fired = inverted_count >= 3  # inverted in 3 of last 5 observations
    return fired, {"T10Y2Y_latest": spread, "inverted_observations": inverted_count}


async def evaluate_sahm_recession(db: AsyncSession) -> tuple[bool, dict]:
    sahm = await get_latest_value(db, "SAHMREALTIME")
    if sahm is None:
        return False, {}
    return sahm >= 0.5, {"SAHMREALTIME": sahm}


async def evaluate_stagflation(db: AsyncSession) -> tuple[bool, dict]:
    cpi_mom = await get_mom_change(db, "CPIAUCSL")
    gdp_vals = await get_recent_values(db, "GDPC1", n=2)
    if cpi_mom is None or len(gdp_vals) < 2:
        return False, {}
    gdp_qoq = ((gdp_vals[0] - gdp_vals[1]) / abs(gdp_vals[1])) * 100 if gdp_vals[1] != 0 else None
    if gdp_qoq is None:
        return False, {}
    fired = cpi_mom > 0.3 and gdp_qoq < 0.5
    return fired, {"CPI_MoM_pct": round(cpi_mom, 3), "GDP_QoQ_pct": round(gdp_qoq, 3)}


async def evaluate_ppi_cpi_squeeze(db: AsyncSession) -> tuple[bool, dict]:
    ppi_yoy = await get_yoy_change(db, "PPIACO")
    cpi_yoy = await get_yoy_change(db, "CPIAUCSL")
    if ppi_yoy is None or cpi_yoy is None:
        return False, {}
    gap = ppi_yoy - cpi_yoy
    fired = gap > 3.0
    return fired, {"PPI_YoY": round(ppi_yoy, 2), "CPI_YoY": round(cpi_yoy, 2), "gap_pp": round(gap, 2)}


async def evaluate_reflation(db: AsyncSession) -> tuple[bool, dict]:
    cpi_yoy = await get_yoy_change(db, "CPIAUCSL")
    gdp_vals = await get_recent_values(db, "GDPC1", n=3)
    if cpi_yoy is None or len(gdp_vals) < 3:
        return False, {}
    gdp_accelerating = gdp_vals[0] > gdp_vals[1] > 0
    fired = gdp_accelerating and cpi_yoy < 2.5
    return fired, {"CPI_YoY": round(cpi_yoy, 2), "GDP_trend": "accelerating" if gdp_accelerating else "decelerating"}


# Map signal names to their evaluator functions
EVALUATORS = {
    "Yield Curve Inversion":    evaluate_yield_curve_inversion,
    "Sahm Recession Alert":     evaluate_sahm_recession,
    "Stagflation Alert":        evaluate_stagflation,
    "PPI-CPI Margin Squeeze":   evaluate_ppi_cpi_squeeze,
    "Reflation Signal":         evaluate_reflation,
}


async def run_signal_engine(db: AsyncSession):
    """Evaluate all signals. Fire any that trigger and are not in cooldown."""
    registry = load_registry()
    logger.info(f"Evaluating {len(registry)} signals...")
    fired_signals = []

    for signal_def in registry:
        evaluator = EVALUATORS.get(signal_def.name)
        if not evaluator:
            logger.warning(f"No evaluator for signal: {signal_def.name}")
            continue

        in_cooldown = await is_in_cooldown(db, signal_def.name, cooldown_hours=24)
        if in_cooldown:
            logger.debug(f"  {signal_def.name} — in cooldown, skipping")
            continue

        try:
            should_fire, snapshot = await evaluator(db)
            if should_fire:
                new_signal = await fire_signal(db, signal_def, snapshot)
                fired_signals.append(new_signal)
        except Exception as e:
            logger.error(f"  Error evaluating {signal_def.name}: {e}")

    logger.info(f"Signal evaluation complete. {len(fired_signals)} signals fired.")
    return fired_signals
