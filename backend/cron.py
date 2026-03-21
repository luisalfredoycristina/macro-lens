"""
Cron entry point. Run via: python -m backend.cron
On Railway: set Start Command to `python -m backend.cron`
On local: `python -m backend.cron --full-backfill` for initial load
"""
import asyncio
import logging
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


async def run(full_backfill: bool = False):
    from backend.db.database import init_db, AsyncSessionLocal
    from backend.fetchers.fred import run_fred_fetcher
    from backend.fetchers.worldbank import run_worldbank_fetcher
    from backend.signals.engine import run_signal_engine
    from backend.alerts.dispatcher import dispatch_pending_alerts

    await init_db()

    async with AsyncSessionLocal() as db:
        logger.info("=== Macro Lens Cron: Starting ===")
        logger.info("Step 1/4: Fetching FRED data...")
        await run_fred_fetcher(db, full_backfill=full_backfill)

        logger.info("Step 2/4: Fetching World Bank data...")
        await run_worldbank_fetcher(db)

        logger.info("Step 3/4: Evaluating signals...")
        fired = await run_signal_engine(db)

        logger.info("Step 4/4: Dispatching alerts...")
        await dispatch_pending_alerts(db)

        logger.info(f"=== Cron complete. {len(fired)} signal(s) fired. ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-backfill", action="store_true",
                        help="Fetch full history from 2000 (for initial setup)")
    args = parser.parse_args()
    asyncio.run(run(full_backfill=args.full_backfill))
