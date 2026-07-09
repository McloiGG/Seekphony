#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/seekphony-uv-cache}"

PYTHON_CMD=(python)
if ! command -v python >/dev/null 2>&1; then
  UV_BIN="${UV_BIN:-uv}"
  if ! command -v "$UV_BIN" >/dev/null 2>&1; then
    echo "python or uv is required but neither was found on PATH." >&2
    exit 1
  fi

  UV_BACKEND_DIR="$REPO_ROOT/backend"
  if command -v cygpath >/dev/null 2>&1; then
    UV_BACKEND_DIR="$(cygpath -w "$UV_BACKEND_DIR")"
  elif [[ "$UV_BACKEND_DIR" == /mnt/[A-Za-z]/* ]]; then
    DRIVE="${UV_BACKEND_DIR:5:1}"
    REST="${UV_BACKEND_DIR:7}"
    UV_BACKEND_DIR="${DRIVE^^}:\\${REST//\//\\}"
  fi
  PYTHON_CMD=("$UV_BIN" run --project "$UV_BACKEND_DIR" python)
fi

curl_file_path() {
  local path="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$path"
  elif [[ "$path" == /mnt/[A-Za-z]/* ]]; then
    local drive="${path:5:1}"
    local rest="${path:7}"
    printf '%s:/%s' "${drive^^}" "$rest"
  else
    printf '%s' "$path"
  fi
}

"${PYTHON_CMD[@]}" - "$TMP_DIR" <<'PY'
from __future__ import annotations

import math
import sys
import wave
from pathlib import Path

target = Path(sys.argv[1])
sample_rate = 16_000

for filename, frequency in (("reference.wav", 440.0), ("performance.wav", 440.0)):
    path = target / filename
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_rate * 6):
            sample = 0.45 * math.sin(2 * math.pi * frequency * (index / sample_rate))
            frames.extend(int(sample * 32767).to_bytes(2, "little", signed=True))
        writer.writeframes(bytes(frames))
PY

REFERENCE_FILE="$(curl_file_path "$TMP_DIR/reference.wav")"
PERFORMANCE_FILE="$(curl_file_path "$TMP_DIR/performance.wav")"

curl -fsS "$BASE_URL/api/v1/health"
curl -fsS \
  -F "reference=@$REFERENCE_FILE;type=audio/wav" \
  -F "performance=@$PERFORMANCE_FILE;type=audio/wav" \
  -F "clip_start_seconds=0" \
  -F "clip_duration_seconds=5" \
  -F "performance_start_seconds=0" \
  "$BASE_URL/api/v1/evaluations"
