# Seekphony

Seekphony is an explainable reference-match singing evaluator. Users upload a
song or backing track, select a short reference clip, record or upload their own
singing, and receive structured scores for pitch, rhythm, stability, coverage,
audio quality, and AI explanation state.

The product is not a universal singing talent judge. It measures how closely a
performance matches the selected reference clip.

## Requirements Alignment

- Data component: persisted evaluation records with file hashes, scores, metrics,
  weak segments, warnings, and Gemini explanation metadata.
- AI component: Gemini explains structured metrics when configured; failures are
  reported without blocking deterministic scores.
- Frontend application: React + TypeScript SPA for upload, clip selection,
  microphone recording, evaluation results, and backend-unavailable states.
- Backend application: FastAPI service with `/api/v1` health and evaluation APIs.
- Integration layer: uv, ruff, pinned dependencies, Docker, Docker Compose,
  optional Postgres through `DATABASE_URL`, env examples, CI, and smoke checks.

## Architecture

```text
Reference audio + clip settings + performance audio
-> React SPA validation
-> FastAPI multipart endpoint
-> audio decoding and clip extraction
-> deterministic pitch/rhythm/quality scoring
-> optional Gemini explanation from structured metrics
-> SQLite or Postgres evaluation persistence
-> frontend scorecards, warnings, weak segments, and explanation display
```

See `docs/ARCHITECTURE.md` and `docs/API_CONTRACT.md` for more detail.

## Prerequisites

- Python `3.14.*`
- `uv` `0.8.*`
- Node.js `22.18.0` or compatible Node 22 runtime
- npm `10.9.3` or compatible npm 10 runtime
- Docker and Docker Compose for container workflows

The backend supports WAV directly. The backend Docker image installs `ffmpeg` so
deployed/containerized runs can decode common uploaded formats such as MP3, M4A,
WebM, OGG, and FLAC when `ffmpeg` supports them.

## Environment Files

Tracked examples are safe placeholders:

- Root `.env.example`: Docker Compose configuration.
- `backend/.env.example`: direct backend and backend Docker configuration.
- `frontend/.env.example`: frontend local and frontend Docker public config.

Local `.env` files are ignored by Git. Do not commit real keys.

Important backend variables:

- `DATABASE_URL`: optional Postgres connection string for deployment. Leave empty
  for local SQLite.
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`: optional Gemini explanation key.
- `SEEKPHONY_GEMINI_MODEL`: Gemini model name. Default:
  `gemini-3.1-flash-lite`.
- `SEEKPHONY_CORS_ORIGINS`: comma-separated allowed browser origins.
- `SEEKPHONY_MAX_UPLOAD_BYTES`: per-file upload/import limit. Default is
  `31457280` bytes / `30 MB`.
- `SEEKPHONY_MIN_CLIP_SECONDS` and `SEEKPHONY_MAX_CLIP_SECONDS`: clip limits.

Public frontend variables:

- `VITE_API_BASE_URL` for Vite local development.
- `SEEKPHONY_PUBLIC_API_BASE_URL` for the built frontend container.

Frontend variables are browser-visible and must not contain secrets.

## Run With Docker Compose

Compose starts the backend on `http://localhost:8000` and the frontend on
`http://localhost:5173`.

```bash
cp .env.example .env
docker compose up --build
```

The frontend service has no hard dependency on backend startup. If the backend is
stopped or fails, the SPA still loads and shows readable backend-unavailable
states.

Run only one service when needed:

```bash
docker compose up --build backend
docker compose up --build frontend
```

## Run Services Locally

Backend:

```bash
cd backend
cp .env.example .env
uv sync --frozen
uv run uvicorn seekphony_backend.main:app --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open the SPA at `http://localhost:5173`.

## Build Individual Docker Containers

Backend image:

```bash
cp backend/.env.example backend/.env
docker build -f backend/Dockerfile -t seekphony-backend .
docker run --rm --env-file backend/.env --mount source=seekphony-backend-data,target=/app/var -p 8000:8000 seekphony-backend
```

Frontend image:

```bash
cp frontend/.env.example frontend/.env
docker build -f frontend/Dockerfile -t seekphony-frontend .
docker run --rm --env-file frontend/.env -p 5173:80 seekphony-frontend
```

For direct frontend Docker runs, set `SEEKPHONY_PUBLIC_API_BASE_URL` to the backend
URL reachable from the browser.

## Deployment Guide

Recommended MVP deployment:

```text
Frontend: Vercel
Backend: Render Docker Web Service
Database: Neon Postgres
Secrets: Render environment variables only
```

1. Create a Neon Postgres database and copy its pooled connection string.
2. Create a Render Docker Web Service from this repo.
3. Configure Render:
   - Dockerfile path: `backend/Dockerfile`
   - `DATABASE_URL=<Neon connection string>`
   - `GEMINI_API_KEY=<optional Gemini key>`
   - `SEEKPHONY_CORS_ORIGINS=*` for first smoke test
4. Verify backend health:
   - `https://your-render-service.onrender.com/api/v1/health`
5. Create a Vercel project with root directory `frontend`.
6. Configure Vercel:
   - Build command: `npm run build`
   - Output directory: `dist`
   - `VITE_API_BASE_URL=https://your-render-service.onrender.com`
7. After Vercel gives a final URL, tighten Render CORS:
   - `SEEKPHONY_CORS_ORIGINS=https://your-vercel-app.vercel.app`
8. Smoke-test the deployed flow from the Vercel UI.

Public deployment should happen after the local Docker Compose flow is stable.

## Checks

Full repository loop:

```bash
scripts/check.sh
```

Backend-only:

```bash
cd backend
uv run ruff format --check . ../scripts
uv run ruff check . ../scripts
uv run pytest
```

Frontend-only:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

With a backend server running, smoke-check the evaluator API:

```bash
scripts/smoke.sh
```

## Key API Routes

- `GET /api/v1/health`
- `POST /api/v1/reference-audio/import`
- `POST /api/v1/evaluations`
- `GET /api/v1/evaluations`
- `GET /api/v1/evaluations/{evaluation_id}`
- `DELETE /api/v1/evaluations/{evaluation_id}`
- `DELETE /api/v1/evaluations`

## Features

- Upload a reference song or backing clip, or import one from a direct audio URL
  or best-effort YouTube link.
- Play loaded reference and performance audio before evaluation.
- Select a 5-60 second performance window; the reference clip uses the same
  duration from the chosen reference start.
- Upload singing audio or record a browser WAV take with an overwrite warning.
- Compare pitch, rhythm, stability, coverage, and audio quality.
- Detect likely key shift and report it instead of treating every transposition as
  a full failure.
- Show warnings for low-confidence, quiet, clipped, or low-voicing audio.
- Persist structured evaluation history, inspect saved result details, and delete
  one or all saved metadata records.
- Display Gemini explanation when configured; show explicit unavailable/error
  state otherwise.

## Technical Decisions

- WAV-first deterministic scoring avoids large audio ML dependencies and Python
  3.14 compatibility risk.
- `ffmpeg` is installed in the backend Docker image for broader upload decoding.
- `yt-dlp==2026.7.4` powers best-effort YouTube reference import. Direct uploads
  and direct audio URLs remain the more reliable MVP path.
- Gemini is used for explanation only, not metric calculation.
- Raw audio is processed transiently and not stored permanently.
- SQLite is the local default; `DATABASE_URL` switches deployment to Postgres.
- The frontend encodes microphone recordings as WAV so local development does not
  require WebM decoding.

## Limitations

- Scoring is a reference-match estimate, not a universal singing-quality grade.
- No lyrics or pronunciation scoring in the MVP.
- No auth, user accounts, permanent audio storage, or analytics dashboard yet.
- Saved evaluation history does not replay old audio because raw audio is not
  stored permanently.
- YouTube import is best effort and may fail when the provider blocks extraction
  or hosted resources are too limited.
- Non-WAV local native runs require `ffmpeg` on PATH.
- Render free resources may be slow for long clips, so the backend enforces short
  clip limits.
- Gemini may be unavailable, rate-limited, or unconfigured; metrics still return.
