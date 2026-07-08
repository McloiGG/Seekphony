#!/usr/bin/env bash
set -euo pipefail

export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/seekphony-uv-cache}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

UV_BIN="${UV_BIN:-uv}"
if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  if command -v uv.exe >/dev/null 2>&1; then
    UV_BIN="uv.exe"
  else
    echo "uv is required but was not found on PATH." >&2
    exit 1
  fi
fi

UV_REPO_ROOT="$REPO_ROOT"
if command -v cygpath >/dev/null 2>&1; then
  UV_REPO_ROOT="$(cygpath -w "$REPO_ROOT")"
elif [[ "$REPO_ROOT" == /mnt/[A-Za-z]/* ]]; then
  DRIVE="${REPO_ROOT:5:1}"
  REST="${REPO_ROOT:7}"
  UV_REPO_ROOT="${DRIVE^^}:\\${REST//\//\\}"
fi

"$UV_BIN" run --project "$UV_REPO_ROOT/backend" python "$UV_REPO_ROOT/scripts/check_tool_versions.py"
"$UV_BIN" run --project "$UV_REPO_ROOT/backend" python "$UV_REPO_ROOT/scripts/check_pyproject_dependencies.py"
"$UV_BIN" run --project "$UV_REPO_ROOT/backend" python "$UV_REPO_ROOT/scripts/check_no_secrets.py"
"$UV_BIN" run --project "$UV_REPO_ROOT/backend" python "$UV_REPO_ROOT/scripts/check_conventional_commits.py"

cd "$REPO_ROOT/backend"

"$UV_BIN" run ruff format --check . ../scripts
"$UV_BIN" run ruff check . ../scripts
"$UV_BIN" run pytest

cd "$REPO_ROOT/Frontend"

npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
