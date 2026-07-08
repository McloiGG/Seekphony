# ExecPlan: Pivot Seekphony Into an Explainable Singing Evaluator

This ExecPlan follows `.agent/PLANS.md`.

## Status

completed

## Purpose / Big Picture

Rebuild Seekphony into a deployable MVP for reference-match singing evaluation. A user uploads a reference song, selects a short clip, records or uploads their performance, and receives deterministic audio metrics plus a Gemini-generated explanation when available.

The visible product becomes a singing practice tool, not a generic music search or humming-recognition app.

## Requirement Link

- Data component: evaluation records, file hashes, metrics JSON, weak-segment JSON, and Gemini explanation metadata persisted locally or through `DATABASE_URL`.
- AI component: Gemini explains structured audio metrics; model failure is visible and does not block deterministic scores.
- Frontend application: React SPA for reference upload, clip selection, recording/uploading performance audio, results, and backend-unavailable states.
- Backend application: FastAPI service with evaluation routes and modular audio, AI, database, and API layers.
- Integration layer: env files, Docker Compose, optional deployment database, CORS, and service-specific env examples.
- Validation/fallback: invalid uploads, excessive clip length, undecodable audio, low-confidence audio, and Gemini errors return structured responses.
- Rubric category: problem impact, solution quality, technical implementation, demo readiness, and technical understanding.

## Context and Orientation

The repository currently contains a completed humming/text song-recognition app. The pivot will remove or replace catalog/search/playback/provider behavior that no longer fits:

- seeded song catalog under `data/seeds/`
- song search, add-song, play-session, recognition-history APIs
- ACRCloud/Shazamio provider paths
- humming/search frontend flows
- old smoke checks that call `/songs`, `/search`, and `/analytics`

The existing FastAPI, React/Vite, Docker, Compose, env-template, and CI structure should be reused.

## Non-Goals

- No auth or user accounts.
- No seeded demo songs.
- No permanent raw-audio storage.
- No lyrics or pronunciation scoring.
- No analytics dashboard.
- No migration framework before the first deploy.
- No public deployment before the local Docker Compose flow works.

## Proposed Approach

Implement a narrow evaluation pipeline:

1. API receives a reference audio file, performance audio file, reference clip start, clip duration, and optional performance start.
2. Backend validates size, extension/content type, clip duration, and audio decodability.
3. Backend decodes WAV directly and optionally uses `ffmpeg` when available for other uploaded formats.
4. Audio service extracts frame-level RMS, voicing, and pitch using deterministic signal processing.
5. Scoring service estimates timing offset, key shift, pitch error, rhythm similarity, pitch stability, coverage, audio quality, and weak segments.
6. Explanation service sends only structured metrics/warnings to Gemini. If Gemini is unavailable or fails, metrics still return and explanation status records the issue.
7. Database persists evaluation metadata and structured result JSON with SQLite by default and Postgres when `DATABASE_URL` is set.
8. Frontend displays upload/record controls, clip constraints, results, warnings, and explanation status.

Dependency rule:

- Prefer lightweight deterministic analysis with standard-library WAV support plus optional `ffmpeg` for deployment decoding.
- Avoid large or Python-3.14-risky audio ML packages unless local dependency resolution proves safe.

## Data Flow

reference upload + clip selection + performance recording/upload
-> FastAPI multipart validation
-> audio decoding and clip extraction
-> pitch/rhythm/quality analysis
-> structured scoring result
-> optional Gemini explanation
-> database evaluation record
-> frontend scorecards, metrics, warnings, weak segments, and explanation state

## Files Expected to Change

- `backend/src/seekphony_backend/`
- `backend/tests/`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `Frontend/src/`
- `Frontend/index.html`
- `Frontend/package.json`
- `README.md`
- `docs/API_CONTRACT.md`
- `docs/ARCHITECTURE.md`
- `.env.example`
- `backend/.env.example`
- `Frontend/.env.example`
- `docker-compose.yml`
- `backend/Dockerfile`
- `scripts/check.sh`
- `scripts/smoke.sh`
- `.github/workflows/ci.yml`
- `plans/active/004-singing-evaluator-pivot.md`

## Milestones

1. Save this approved ExecPlan and mark it in progress.
2. Replace backend routes, schemas, persistence, and services with evaluation behavior.
3. Add generated-WAV backend tests for valid, shifted, invalid, and Gemini-unavailable cases.
4. Replace frontend UI, API client, types, and tests with evaluator flow.
5. Update Docker/Compose/env/runtime behavior for the evaluator.
6. Update README, architecture docs, API contract, smoke checks, and CI.
7. Sweep legacy terms and remove obsolete files.
8. Run validation and record results.
9. Move this plan to `plans/done/` when complete.

## Progress

- [x] Save approved ExecPlan
- [x] Replace backend evaluation API
- [x] Add backend tests
- [x] Replace frontend evaluator SPA
- [x] Update runtime/docs/scripts/CI
- [x] Sweep legacy behavior
- [x] Run validation
- [x] Complete plan and move to done

## Validation and Acceptance

Run and record:

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- `npm run lint`
- `npm run typecheck`
- `npm test -- --run`
- `npm run build`
- backend smoke check against health and generated-audio evaluation
- Docker Compose build/run when Docker is available

Acceptance criteria:

- Backend exposes only health and evaluation-focused APIs.
- Frontend loads without backend and shows readable unavailable states.
- Evaluation returns metrics even when Gemini is not configured.
- Gemini errors are visible and do not create fake explanations.
- Uploads over configured size or clip-duration limits are rejected.
- Evaluation records persist in SQLite by default.
- `DATABASE_URL` is documented and wired for Postgres deployment.
- Old humming/search/catalog/playback behavior is removed from product docs, tests, and smoke checks.

## Fallback and Error Handling

- Missing files return `validation_error`.
- Unsupported/undecodable audio returns `unsupported_audio` or `audio_decode_failed`.
- Clip duration outside bounds returns `validation_error`.
- Low voiced coverage returns metrics with warnings and lower confidence.
- Gemini missing key returns `explanation.status = "unavailable"`.
- Gemini request or validation failure returns `explanation.status = "error"` with a safe message.
- Database insert failure returns structured backend error.

## Risks and Mitigations

- Risk: Python 3.14 support for advanced audio packages may be weak.
  Mitigation: implement deterministic WAV analysis without requiring heavy ML packages; use optional `ffmpeg` for broader decoding.

- Risk: Browser recordings may produce WebM by default.
  Mitigation: frontend records PCM through Web Audio and encodes WAV before upload.

- Risk: Free Render resources may be tight for long audio.
  Mitigation: enforce short clip duration and size limits.

- Risk: Postgres deployment adds dependency/runtime risk.
  Mitigation: keep SQLite default and use a small raw-SQL adapter for Postgres through `DATABASE_URL`.

## Surprises & Discoveries

- Observation:
  Git initially refused status checks due to dubious ownership.
  Evidence:
  `git status --short` reported the repository needed a `safe.directory` entry. McloiGG ran the recommended command before implementation.

- Observation:
  The local uv executable is newer than the required project version.
  Evidence:
  `scripts/check_tool_versions.py` reported `uv 0.11.20`, while `REQUIREMENTS.md` requires `uv 0.8.*`.

- Observation:
  Docker is not installed or not available on PATH in this environment.
  Evidence:
  `docker --version` failed with `The term 'docker' is not recognized`.

- Observation:
  The implementation avoided heavy audio ML dependencies.
  Evidence:
  Backend tests pass with generated WAV files using deterministic signal analysis and no librosa/ML dependency installation.

## Decision Log

- Decision:
  Keep the product name `Seekphony`.
  Rationale:
  McloiGG explicitly confirmed no rename is needed.
  Date/Author:
  2026-07-08 / McloiGG

- Decision:
  Use env files through Compose `env_file` with `required: false`.
  Rationale:
  McloiGG requested env-file reliance while preserving safe boot behavior.
  Date/Author:
  2026-07-08 / McloiGG

- Decision:
  Gemini explanations do not get a deterministic text fallback.
  Rationale:
  McloiGG requested Gemini errors to be reported while metrics still display.
  Date/Author:
  2026-07-08 / McloiGG

- Decision:
  Use SQLite default plus optional Postgres through `DATABASE_URL`.
  Rationale:
  Local speed and testability matter today, while deployment needs persistent Postgres.
  Date/Author:
  2026-07-08 / McloiGG + Codex

- Decision:
  Use deterministic WAV-first analysis with optional `ffmpeg` decoding in Docker.
  Rationale:
  It reduces Python 3.14 dependency risk and keeps the MVP buildable today.
  Date/Author:
  2026-07-08 / Codex

- Decision:
  Encode browser microphone recordings as WAV in the frontend.
  Rationale:
  Local development should not require WebM decoding or `ffmpeg` for the recording path.
  Date/Author:
  2026-07-08 / Codex

## Validation Results

Validation run on 2026-07-08:

- `uv run ruff format --check . ../scripts`: passed, 18 files already formatted.
- `uv run ruff check . ../scripts`: passed.
- `uv run pytest`: passed, 10 tests.
- `npm.cmd run lint`: passed.
- `npm.cmd run typecheck`: passed.
- `npm.cmd test -- --run`: passed, 3 tests.
- `npm.cmd run build`: passed.
- `scripts/check_pyproject_dependencies.py`: passed.
- `scripts/check_no_secrets.py`: passed.
- `scripts/check_conventional_commits.py`: passed.
- PowerShell backend smoke check against local uvicorn on port 8001: passed for `/health` and generated-WAV `POST /api/v1/evaluations`.
- Legacy sweep for `humming`, `catalog`, `songs`, `ACRCloud`, `Shazamio`, `plays`, old search routes: passed, no product-code/doc matches.

Known validation limitations:

- `scripts/check_tool_versions.py`: failed because local `uv` is `0.11.20`; project requirement is `uv 0.8.*`.
- `docker compose up --build`: not run because Docker is not installed or not available on PATH.

## Outcomes & Retrospective

Completed the MVP pivot:

- Backend now exposes health and evaluation APIs only.
- Deterministic audio metrics, key-shift detection, weak segments, warnings, Gemini explanation state, and persistence are implemented.
- Frontend now supports reference upload, clip settings, performance upload, WAV recording, evaluation submission, results, and recent history.
- Legacy humming/search/catalog/playback/provider functionality was removed from active product surfaces.
- Runtime docs, API contract, architecture docs, env examples, Dockerfile, Compose, smoke checks, tests, and README now describe the evaluator.

Remaining follow-ups:

- Install/use `uv 0.8.*` for strict local tool-version compliance.
- Run Docker build/Compose validation on a machine with Docker installed.
- Deploy backend to Render with Neon `DATABASE_URL`, then deploy frontend to Vercel and tighten CORS.
