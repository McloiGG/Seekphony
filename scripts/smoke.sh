#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

python - "$TMP_DIR" <<'PY'
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

curl -fsS "$BASE_URL/health"
curl -fsS \
  -F "reference=@$TMP_DIR/reference.wav;type=audio/wav" \
  -F "performance=@$TMP_DIR/performance.wav;type=audio/wav" \
  -F "clip_start_seconds=0" \
  -F "clip_duration_seconds=5" \
  -F "performance_start_seconds=0" \
  "$BASE_URL/api/v1/evaluations"
