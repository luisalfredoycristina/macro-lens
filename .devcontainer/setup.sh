#!/bin/bash
set -e

echo "=== Setting up Macro Lens ==="

# ── PostgreSQL ──────────────────────────────────────────────────────────────
echo "→ Starting PostgreSQL..."
sudo service postgresql start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" 2>/dev/null || true
sudo -u postgres createdb macrolens 2>/dev/null || echo "  DB already exists"

# ── Backend ─────────────────────────────────────────────────────────────────
echo "→ Installing backend dependencies..."
cd /workspaces/macro-lens/backend
pip install --quiet poetry
poetry config virtualenvs.create false
poetry install --no-interaction --quiet

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created backend/.env — add your FRED_API_KEY to it"
fi

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "→ Installing frontend dependencies..."
cd /workspaces/macro-lens/frontend
npm install --silent

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Open backend/.env and set FRED_API_KEY=your_key"
echo "  2. Start backend:  cd backend && uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  3. Start frontend: cd frontend && npm run dev"
echo "  4. Load data:      python -m backend.cron --full-backfill"
