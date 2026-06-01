#!/usr/bin/env bash
# Smoke test for M2 auth + health. Owner: M2.
# Hits a RUNNING backend and asserts the full login -> JWT -> /me flow works.
# Prints PASS/FAIL per check and exits non-zero on any failure.
#
# Usage:
#   bash scripts/smoke_test.sh                 # defaults to http://localhost:8000
#   BASE_URL=http://localhost:8000 \
#   ADMIN_EMAIL=admin@iisc-demo.com \
#   ADMIN_PASSWORD=changeme-strong-password \
#       bash scripts/smoke_test.sh
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${SEED_ADMIN_EMAIL:-admin@iisc-demo.com}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${SEED_ADMIN_PASSWORD:-changeme-strong-password}}"

pass=0; fail=0
ok()   { echo "  ✅ PASS: $1"; pass=$((pass+1)); }
bad()  { echo "  ❌ FAIL: $1"; fail=$((fail+1)); }

echo "== Smoke test against ${BASE_URL} =="

# 1. /health
echo "[1] GET /health"
health=$(curl -s "${BASE_URL}/health")
echo "    -> ${health}"
echo "${health}" | grep -q '"status": *"ok"' && ok "health status ok" || bad "health not ok"
echo "${health}" | grep -q '"database": *"connected"' && ok "database connected" || bad "database not connected"

# 2. /auth/login
echo "[2] POST /auth/login"
login=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")
token=$(echo "${login}" | sed -n 's/.*"access_token": *"\([^"]*\)".*/\1/p')
if [ -n "${token}" ]; then ok "login returned JWT"; else bad "login returned no token -> ${login}"; fi

# 3. wrong password -> 401
echo "[3] POST /auth/login (wrong password expects 401)"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${BASE_URL}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"definitely-wrong\"}")
[ "${code}" = "401" ] && ok "wrong password -> 401" || bad "wrong password -> ${code} (expected 401)"

# 4. /auth/me with token -> 200
echo "[4] GET /auth/me (with token expects 200)"
if [ -n "${token}" ]; then
  me=$(curl -s -w '\n%{http_code}' "${BASE_URL}/auth/me" -H "Authorization: Bearer ${token}")
  body=$(echo "${me}" | head -n1); code=$(echo "${me}" | tail -n1)
  echo "    -> ${body}"
  [ "${code}" = "200" ] && ok "/me with token -> 200" || bad "/me with token -> ${code}"
else
  bad "/me skipped (no token)"
fi

# 5. /auth/me without token -> 401
echo "[5] GET /auth/me (no token expects 401)"
code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/auth/me")
[ "${code}" = "401" ] && ok "/me without token -> 401" || bad "/me without token -> ${code}"

echo "== ${pass} passed, ${fail} failed =="
[ "${fail}" -eq 0 ]
