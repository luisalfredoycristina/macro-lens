"""
Alert dispatcher. Sends email via SendGrid and/or POSTs to a webhook URL.
"""
import os
import httpx
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.models import Signal, AlertConfig

logger = logging.getLogger(__name__)


async def send_webhook(webhook_url: str, signal: Signal):
    payload = {
        "text": f"🚨 *{signal.signal_name}* | {signal.direction} | Conviction: {signal.conviction}/3",
        "attachments": [{
            "color": "#E8593C" if signal.direction == "BEARISH" else "#1D9E75",
            "fields": [
                {"title": "Trade Implication", "value": signal.trade_implication, "short": False},
                {"title": "Data", "value": str(signal.data_snapshot), "short": False},
                {"title": "Fired At", "value": str(signal.fired_at), "short": True},
            ]
        }]
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=10.0)
            resp.raise_for_status()
            logger.info(f"Webhook sent for signal: {signal.signal_name}")
    except Exception as e:
        logger.error(f"Webhook failed: {e}")


async def send_email(to_email: str, signal: Signal):
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("SENDGRID_API_KEY not set, skipping email alert")
        return
    html = f"""
    <h2>Macro Lens Signal Alert</h2>
    <p><strong>Signal:</strong> {signal.signal_name}</p>
    <p><strong>Direction:</strong> {signal.direction}</p>
    <p><strong>Conviction:</strong> {signal.conviction}/3</p>
    <p><strong>Trade Implication:</strong> {signal.trade_implication}</p>
    <p><strong>Data Snapshot:</strong> {signal.data_snapshot}</p>
    <p><strong>Fired At:</strong> {signal.fired_at}</p>
    """
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": "alerts@macrolens.app", "name": "Macro Lens"},
        "subject": f"🚨 Signal: {signal.signal_name} ({signal.direction})",
        "content": [{"type": "text/html", "value": html}]
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info(f"Email sent for signal: {signal.signal_name}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")


async def dispatch_pending_alerts(db: AsyncSession):
    """Find all unsent signals and dispatch alerts."""
    config_result = await db.execute(select(AlertConfig).limit(1))
    config = config_result.scalar_one_or_none()

    result = await db.execute(
        select(Signal).where(Signal.alert_sent == False).order_by(Signal.fired_at)
    )
    pending = result.scalars().all()

    for signal in pending:
        if config and config.email:
            await send_email(config.email, signal)
        elif os.getenv("ALERT_EMAIL"):
            await send_email(os.getenv("ALERT_EMAIL"), signal)

        if config and config.webhook_url:
            await send_webhook(config.webhook_url, signal)
        elif os.getenv("WEBHOOK_URL"):
            await send_webhook(os.getenv("WEBHOOK_URL"), signal)

        signal.alert_sent = True

    if pending:
        await db.commit()
        logger.info(f"Dispatched {len(pending)} alert(s)")
