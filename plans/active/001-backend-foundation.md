# ExecPlan: Build Backend Foundation

This ExecPlan follows `.agent/PLANS.md`.

## Status

completed

## Purpose / Big Picture

Build Seekphony's backend as a standalone FastAPI service. Any frontend should be able to call documented APIs to search songs by text or uploaded audio, add songs, reject duplicates, record listening sessions, and read analytics.

SongPi is used only as product and architecture inspiration: optional Shazamio recognition, metadata extraction, recognition/play history, last recognized song persistence, timeout/retry/fallback behavior, and troubleshooting-friendly structured errors.

## Requirement Link

- Data component: SQLite catalog, seeded song data, local normalization, file hashing, metadata storage, recognition history, and play/session history.
- AI component: provider-swappable model/AI path with structured outputs, validation, and fallback handling.
- Backend application: FastAPI service with modular API, data, AI, matching, and analytics layers.
- Frontend application: not implemented here; frontend consumes documented backend contracts.
- Integration layer: `.env.example`, `backend/Dockerfile`, backend-only Compose service, uv, ruff, pinned dependencies.
- Validation/fallback: backend boots and tests without Gemini/Shazamio, but at least one meaningful AI/model-based provider path must be demoable for evaluation.
- Rubric category: technical implementation, solution quality, maintainability, demo readiness.

## Context and Orientation

The repo currently has harness docs, `REQUIREMENTS.md`, `.agent/PLANS.md`, `docs/ARCHITECTURE.md`, an empty `docs/API_CONTRACT.md`, and scripts. Backend implementation is being added under `backend/`.

McloiGG owns backend implementation. Ridzuanbkr owns frontend implementation. The backend must run independently and treat the frontend as an external API consumer.

SongPi reference boundaries:
- Use as inspiration for recognition architecture and failure handling.
- Do not copy SongPi code.
- Do not implement Tkinter, desktop UI, PyAudio microphone device selection, or always-on listening.
- Audio capture belongs to the frontend. Backend only accepts uploaded audio blobs/files.

## Non-Goals

- No frontend UI implementation.
- No always-on listening daemon.
- No PyAudio microphone/device management.
- No Tkinter or desktop display features.
- No paid service dependency.
- No requirement for Gemini or Shazamio to boot the backend or run tests.
- No guarantee that every streaming URL can be extracted.

## Proposed Approach

Create a modular FastAPI backend under `backend/` with clear separation between routes, settings, data persistence, AI providers, recognition, matching, and analytics.

Use SQLite as the runtime database and seed it from tracked catalog data. Local normalization, duplicate detection, file hashing, and deterministic matching are core backend behavior. Gemini text extraction and URL metadata extraction are optional/best-effort provider behavior.

Canonical routes use `/api/v1`. Compatibility aliases may exist for the prototype frontend, but aliases must call the same services as canonical routes.

Implement SongPi-inspired backend behavior:
- optional Shazamio provider for uploaded audio recognition
- optional Gemini provider for structured text/metadata extraction
- metadata extraction from uploaded files and best-effort URLs
- recognition history table recording query type, provider, result, confidence, status, and fallback reason
- play/session history table for analytics
- last recognized song persisted in database
- configurable provider timeout, retry count, and retry delay
- structured errors with status codes such as `duplicate_detected`, `not_found`, `provider_unavailable`, `validation_error`, and `extraction_failed`

## Data Flow

Text search:

user text -> FastAPI validation -> Gemini provider if configured -> local extractor fallback -> catalog matcher -> structured `found`, `candidates`, or `not_found` response -> recognition history update

Audio search:

uploaded audio blob/file -> FastAPI validation -> optional Shazamio provider with timeout/retry -> local metadata/hash fallback -> catalog matcher -> structured response -> recognition history and last recognized song update

Add song:

metadata plus optional file/URL -> validation -> local normalization and file hashing -> optional metadata extraction -> duplicate checks -> SQLite insert -> structured song response

Playback analytics:

frontend starts/stops play session -> backend records session duration -> analytics endpoint aggregates top songs, total time, recent sessions, recognition history, and last recognized song

## Files Expected to Change

- `backend/`
- `backend/Dockerfile`
- `data/seeds/`
- `docs/API_CONTRACT.md`
- `README.md`
- `.env.example`
- `docker-compose.yml`
- `scripts/check.sh`
- `scripts/smoke.sh`
- `tests/`
- `plans/active/001-backend-foundation.md`

The `.agents/` to `.agent/` harness rename is already reflected in the working tree and should be recorded intentionally in Git when staging.

## Milestones

1. Save this approved ExecPlan to `plans/active/001-backend-foundation.md`.
2. Scaffold backend package, project config, pinned dependencies, health endpoint, and `backend/Dockerfile`.
3. Document `/api/v1` canonical API contract and compatibility aliases in `docs/API_CONTRACT.md`.
4. Add SQLite schema and seed data.
5. Implement catalog, local normalization, file hashing, and duplicate logic.
6. Implement text matching and provider-swappable AI interface.
7. Implement SongPi-inspired uploaded-audio recognition provider behavior.
8. Implement metadata extraction with core local behavior and optional/best-effort Gemini or URL behavior.
9. Implement recognition history, last recognized song persistence, play sessions, and analytics.
10. Add tests, smoke checks, README updates, and validation results.
11. Keep this ExecPlan updated throughout implementation.

## Progress

- [x] Save approved ExecPlan
- [x] Scaffold backend package and project config
- [x] Document API contract
- [x] Add SQLite schema and seed data
- [x] Implement catalog and duplicate logic
- [x] Implement text matching and AI provider interface
- [x] Implement SongPi-inspired uploaded-audio recognition provider behavior
- [x] Implement metadata extraction
- [x] Implement recognition history and last recognized song persistence
- [x] Implement play session analytics
- [x] Add Docker backend setup
- [x] Add tests and smoke checks
- [x] Update README and validation results

## Validation and Acceptance

Run and record:

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- backend smoke test against health, songs, search, add-song, analytics
- Docker build and backend container smoke test

Acceptance criteria:
- Backend boots without Gemini or Shazamio credentials.
- Tests run without network or secrets.
- At least one meaningful AI/model-based provider path is demoable for evaluation.
- `/api/v1` routes are canonical.
- Compatibility aliases reuse the same business logic.
- Text search returns structured results.
- Audio endpoint accepts uploaded audio blobs/files.
- Provider failures are visible and do not crash normal demo flow.
- Duplicate song attempts return status `duplicate_detected`.
- Analytics include play counts, total listening time, recent sessions, recognition history, and last recognized song.
- No frontend UI files are implemented.

## Fallback and Error Handling

- Invalid input returns structured 4xx errors with `validation_error`.
- Missing catalog entries return `not_found` with optional ranked candidates.
- Duplicate attempts return `duplicate_detected`.
- Gemini unavailable returns local extraction fallback with `fallback_used: true`.
- Shazamio unavailable, timeout, or no match returns structured fallback information.
- URL extraction failures return `unsupported_source` or `extraction_failed` without blocking manual song entry.
- Duplicate detection checks normalized title+artist, source URL, and uploaded file SHA-256 where present.
- Recognition errors include provider, stage, retryable, fallback_used, and user-safe message.

## Risks and Mitigations

- Shazamio is unofficial and network-sensitive.
  Mitigation: optional provider, timeout/retry config, local fallback, no boot/test dependency.

- Gemini free tier may be unavailable or rate-limited.
  Mitigation: optional key and deterministic local extraction fallback.

- Evaluation requires meaningful AI/model-based behavior.
  Mitigation: prepare at least one demoable provider path, preferably Gemini text extraction or Shazamio audio recognition.

- URL extraction can be inconsistent across platforms.
  Mitigation: best-effort metadata only, clear unsupported-source errors.

- Python 3.14 dependency support may be uneven.
  Mitigation: keep dependency set small and pinned; avoid unnecessary audio-native packages.

- Frontend contract drift may slow integration.
  Mitigation: `docs/API_CONTRACT.md` is updated before or alongside backend routes.

## Surprises & Discoveries

- Observation:
  `docs/API_CONTRACT.md` existed but was empty before implementation.
  Evidence:
  Local inspection showed file length 0.

- Observation:
  The harness uses `.agent/`, while earlier repo state had `.agents/`.
  Evidence:
  Earlier Git status showed deleted `.agents/PLANS.md` and `.agents/REVIEW.md`, plus untracked `.agent/`; the current status is clean before implementation.

- Observation:
  uv could not use its default cache path in this environment.
  Evidence:
  Initial validation failed with `Failed to initialize cache at C:\Users\jacka\AppData\Local\uv\cache`.

- Observation:
  Optional provider packages should stay dynamic imports for the foundation.
  Evidence:
  An invalid optional `yt-dlp` pin made uv dependency resolution unsatisfiable, so optional provider imports are handled at runtime instead of blocking core boot/tests.

- Observation:
  Docker is not installed or not available on PATH in this environment.
  Evidence:
  `docker --version` and `docker compose version` both failed with `docker : The term 'docker' is not recognized`.

## Decision Log

- Decision:
  Backend accepts uploaded audio only; frontend owns microphone capture.
  Rationale:
  Matches team roles and avoids SongPi desktop/PyAudio scope.
  Date/Author:
  2026-07-01 / McloiGG + Codex

- Decision:
  Use SongPi only as architecture inspiration, not source code.
  Rationale:
  Keeps implementation original and web-backend appropriate.
  Date/Author:
  2026-07-01 / McloiGG

- Decision:
  Make Gemini and Shazamio optional for boot/tests, but require at least one meaningful AI/model-based provider path for evaluation demo.
  Rationale:
  Preserves reliability while satisfying the AI requirement.
  Date/Author:
  2026-07-01 / McloiGG

- Decision:
  `/api/v1` routes are canonical and compatibility aliases must reuse the same business logic.
  Rationale:
  Gives frontend a stable contract without duplicating backend behavior.
  Date/Author:
  2026-07-01 / McloiGG

- Decision:
  Use explicit response statuses including `duplicate_detected`.
  Rationale:
  Makes frontend handling and evaluator explanation clearer than generic errors.
  Date/Author:
  2026-07-01 / McloiGG

- Decision:
  Persist recognition history and last recognized song.
  Rationale:
  Adapts SongPi's history/state persistence idea to backend analytics and demo recovery.
  Date/Author:
  2026-07-01 / Codex

- Decision:
  Implement Gemini through the REST API using the Python standard library instead of adding a required SDK dependency.
  Rationale:
  Keeps the model-based demo path available with only `GEMINI_API_KEY` while preserving no-secret/no-network testability.
  Date/Author:
  2026-07-01 / Codex

## Validation Results

Validation run on 2026-07-01:

- `uv run --project backend ruff format --check backend`: passed after formatting 4 files.
- `uv run --project backend ruff check backend`: passed after import/line-length fixes.
- `uv run --project backend pytest backend/tests`: passed, 7 tests.
- Backend smoke test against temporary uvicorn server: passed for `/health`, `/api/v1/songs`, `/api/v1/search/text`, and `/api/v1/analytics`.
- Docker build/container smoke test: not run because Docker is not installed or not available on PATH in this environment.

Notes:

- Validation used `UV_CACHE_DIR` pointed at a temp directory because the default uv cache path was unusable in this sandbox.
- pytest emitted FastAPI/Python 3.14 deprecation warnings from FastAPI internals, not application test failures.

## Outcomes & Retrospective

Completed backend foundation:

- FastAPI backend with canonical `/api/v1` routes and compatibility aliases.
- SQLite schema, seed loading, catalog CRUD, duplicate detection, recognition history, last recognized song state, play sessions, and analytics.
- SongPi-inspired optional provider behavior without copying SongPi code or implementing frontend/desktop/audio-capture responsibilities.
- API contract, README, environment template, backend Dockerfile, Compose service, validation scripts, and tests.

Remaining follow-ups:

- Run Docker build/smoke on a machine with Docker installed.
- Add Shazamio as an optional demo dependency only after confirming an exact compatible version for Python 3.14.
