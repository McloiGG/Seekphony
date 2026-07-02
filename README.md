# Seekphony

Seekphony is a Week 4 backend-first music discovery system. The backend provides a standalone FastAPI API for text/audio search, catalog management, duplicate rejection, recognition history, play tracking, and analytics.

McloiGG owns backend implementation. Ridzuanbkr owns frontend implementation. This repository phase does not implement frontend UI files; frontend clients integrate through `docs/API_CONTRACT.md`.

## Requirements Alignment

- Data component: SQLite catalog, seed data, file hashing, recognition history, play sessions.
- AI component: provider-swappable Gemini/Shazamio paths with structured local fallback.
- Backend application: FastAPI service with `/api/v1` canonical routes.
- Integration layer: uv, ruff, Docker, service env examples, `.dockerignore`, documented API contract.

## Backend Runtime Modes

Python 3.14 and uv 0.8.* are required by the course guardrails.

### Native/local

The backend can run directly from its service directory. Optional local configuration lives in `backend/.env`, created from `backend/.env.example`; do not commit `backend/.env`.

```bash
cd backend
cp .env.example .env
uv run uvicorn seekphony_backend.main:app --reload
```

The service starts on `http://127.0.0.1:8000`. Injected environment variables override values loaded from `backend/.env`.

### Direct Docker

The backend image builds independently from Compose. Use a named volume for runtime SQLite/uploads mounted at `/app/var`.

```bash
cp backend/.env.example backend/.env
docker build -f backend/Dockerfile -t seekphony-backend .
docker run --rm --env-file backend/.env --mount source=seekphony-backend-data,target=/app/var -p 8000:8000 seekphony-backend
```

`backend/.env.example` uses paths that work from `backend/` natively and from `/app/backend` in the container.

### Docker Compose

The root Compose file is for local orchestration and demos. It uses an optional root `.env` `env_file:` plus explicit `environment:` mappings with safe defaults, so it can boot without a local root `.env`.

```bash
docker compose up --build backend
```

To override defaults locally, copy root `.env.example` to root `.env` first; Compose will load it through the optional `env_file:` entry. Do not commit root `.env`.

```bash
cp .env.example .env
docker compose up --build backend
```

The backend container exposes port `8000` and stores runtime SQLite/uploads in the `seekphony-backend-data` volume mounted at `/app/var`.

### CI/deployment

CI and deployment environments should inject environment variables directly. They do not need local `.env` files, and secrets must never be copied into Docker images.

## Checks

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

With a backend server running, `scripts/smoke.sh` checks health, songs, text search, and analytics endpoints.

## Optional Providers

The backend boots and tests without secrets.

- `GEMINI_API_KEY`: enables Gemini text metadata extraction.
- `SEEKPHONY_ENABLE_SHAZAMIO=true`: enables optional Shazamio audio recognition when the optional package is installed.

Local normalization, file hashing, and deterministic matching remain available when providers are missing.

## Key Endpoints

- `GET /api/v1/health`
- `GET /api/v1/songs`
- `POST /api/v1/songs`
- `POST /api/v1/search/text`
- `POST /api/v1/search/audio`
- `POST /api/v1/extract/file`
- `POST /api/v1/extract/url`
- `POST /api/v1/plays/start`
- `POST /api/v1/plays/{session_id}/stop`
- `GET /api/v1/analytics`

See `docs/API_CONTRACT.md` for compatibility aliases and response shapes.
