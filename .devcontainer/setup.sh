#!/bin/bash
set -e

echo "=== Macro Lens Setup ==="

# ── PostgreSQL ──────────────────────────────────────────────────────────────
echo "→ Setting up PostgreSQL..."
sudo service postgresql start || true
sleep 2
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" 2>/dev/null || true
sudo -u postgres createdb macrolens 2>/dev/null || echo "  macrolens db already exists"

# ── Backend ─────────────────────────────────────────────────────────────────
echo "→ Installing Python dependencies..."
cd /workspaces/macro-lens/backend
pip install --quiet -r requirements.txt

# Create .env if missing
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ✅ Created backend/.env"
fi

# ── Frontend ────────────────────────────────────────────────────────────────
echo "→ Installing Node dependencies..."
cd /workspaces/macro-lens/frontend
npm install --silent

echo ""
echo "✅ All done! Next:"
echo "  1. Add your FRED key: nano /workspaces/macro-lens/backend/.env"
echo "  2. Start backend:     cd /workspaces/macro-lens && uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  3. Start frontend:    cd /workspaces/macro-lens/frontend && npm run dev"
