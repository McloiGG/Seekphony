#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

curl -fsS "$BASE_URL/health"
curl -fsS "$BASE_URL/api/v1/songs"
curl -fsS \
  -H "Content-Type: application/json" \
  -d '{"query":"Blinding Lights by The Weeknd"}' \
  "$BASE_URL/api/v1/search/text"
curl -fsS "$BASE_URL/api/v1/analytics"
