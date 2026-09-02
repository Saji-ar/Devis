#!/usr/bin/env bash
# Lance le backend (port 8000) et le front en mode dev (port 5173) en parallele.
set -e
cd "$(dirname "$0")"

# Backend
( cd backend && [ -d .venv ] || python3 -m venv .venv; \
  ./.venv/bin/pip install -q -r requirements.txt; \
  [ -f .env ] || cp .env.example .env; \
  ./.venv/bin/uvicorn app.main:app --reload --port 8000 ) &
BACK=$!

# Frontend
( cd frontend && [ -d node_modules ] || npm install; npm run dev ) &
FRONT=$!

trap "kill $BACK $FRONT 2>/dev/null" EXIT
echo "Backend : http://localhost:8000/api/health"
echo "Front   : http://localhost:5173"
wait
