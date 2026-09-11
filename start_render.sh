#!/usr/bin/env bash
set -euo pipefail
export FLASK_ENV=production
export BACKEND_API_URL="http://127.0.0.1:5000/api"
python backend/init_deploy.py
python scripts/maintenance/importar_banco_cliente.py
(
  cd backend
  exec gunicorn --workers 2 --threads 2 --timeout 120 --bind 127.0.0.1:5000 run:app
) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT
cd frontend
exec gunicorn --workers 2 --threads 2 --timeout 120 --bind "0.0.0.0:${PORT:-10000}" run:app
