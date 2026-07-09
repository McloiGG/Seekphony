#!/bin/sh
set -eu

cat > /usr/share/nginx/html/config.js <<EOF
window.__SEEKPHONY_CONFIG__ = {
  apiBaseUrl: "${SEEKPHONY_PUBLIC_API_BASE_URL:-http://localhost:8000}"
};
EOF
