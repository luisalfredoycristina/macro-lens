# Macro Lens

Global macro intelligence dashboard — FRED + World Bank APIs, FastAPI backend, Next.js frontend. Cost: $0–5/month.

## Quick Start

### 1. Get a free FRED API key
https://fred.stlouisfed.org/docs/api/api_key.html (30 seconds, no credit card)

### 2. Clone and configure
```bash
cd macro-lens
cp backend/.env.example backend/.env
# Edit backend/.env and set FRED_API_KEY=your_key_here
```

### 3. Start everything
```bash
docker-compose up -d
```

### 4. Run initial data backfill (first time only — fetches from 2020)
```bash
docker-compose exec backend python -m backend.cron --full-backfill
```

### 5. Open the dashboard
http://localhost:3000

### 6. Trigger data refresh manually
```bash
curl -X POST http://localhost:8000/api/run-fetch
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FRED_API_KEY` | YES | Free key from fred.stlouisfed.org |
| `DATABASE_URL` | YES | PostgreSQL connection string |
| `SENDGRID_API_KEY` | Optional | For email alerts |
| `ALERT_EMAIL` | Optional | Recipient email for signal alerts |
| `WEBHOOK_URL` | Optional | Slack/Discord webhook for signal alerts |

## Deployment

### Backend (Railway)
1. Create new Railway project
2. Add PostgreSQL plugin
3. Deploy backend service, set `DATABASE_URL` from Railway's Postgres plugin
4. Set `FRED_API_KEY` env var
5. Add a cron job: `python -m backend.cron` on daily schedule

### Frontend (Vercel)
1. Connect GitHub repo to Vercel
2. Set `NEXT_PUBLIC_API_URL` to your Railway backend URL
3. Deploy

## Adding a Custom Signal

Edit `signals.yaml` only — no Python changes needed for threshold adjustments. To add a new signal type with custom logic, add an entry to `signals.yaml` and a matching evaluator function in `backend/signals/engine.py`, then register it in the `EVALUATORS` dict.

## API Reference

| Endpoint | Description |
|---|---|
| `GET /api/regime` | Current macro regime quadrant |
| `GET /api/indicators` | All 13 FRED indicators with deltas |
| `GET /api/yield-curve` | Yield curve (current + 3m ago) |
| `GET /api/series/{id}` | Time-series history for any FRED series |
| `GET /api/countries` | Country risk table (World Bank) |
| `GET /api/signals` | Signal feed |
| `GET /api/commodities` | Commodity prices and change windows |
| `POST /api/run-fetch` | Manually trigger data refresh |
| `GET /api/health` | Service health check |
