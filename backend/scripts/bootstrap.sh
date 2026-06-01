#!/usr/bin/env bash
# Bootstrap the backend's DB state: run migrations, then seed the demo admin.
# Owner: M2. Idempotent — safe to run repeatedly.
#
# Run from inside the backend container (WORKDIR=/app):
#   docker compose exec backend bash scripts/bootstrap.sh
# Or from the host (backend/ as cwd, deps installed, DB up):
#   cd backend && bash scripts/bootstrap.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # -> backend/

echo "==> alembic upgrade head"
alembic upgrade head

echo "==> seed admin"
python -m scripts.seed_admin

echo "==> done. Try: bash scripts/smoke_test.sh"
