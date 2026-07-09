# ExecPlan: Frontend URL Import and History Enhancements

This ExecPlan follows `.agent/PLANS.md`.

## Status

completed

## Purpose / Big Picture

Improve Seekphony's evaluator before deployment so users can clearly provide a
reference song and performance, confirm playable audio before evaluation, import
reference audio from direct URLs or best-effort YouTube links, and inspect or
delete saved evaluation metadata.

## Requirement Link

- Data component: saved evaluation metadata remains queryable, inspectable, and deletable.
- AI component: Gemini explanation output remains stored with historical result details.
- Frontend application: React SPA gets clearer source selection, playback, trim controls, and history details.
- Backend application: FastAPI adds URL import and history deletion endpoints.
- Integration layer: Docker/env/docs/tests reflect the 30 MB import/upload cap and pinned URL importer dependency.
- Validation/fallback: invalid URLs, import failures, YouTube failures, oversize input, and delete errors are structured.
- Rubric category: usability, maintainability, demo readiness, and integration quality.

## Context and Orientation

The current backend accepts multipart reference and performance uploads at
`POST /api/v1/evaluations`, persists evaluation metadata only, and exposes read
history endpoints. The current frontend has a compact two-file form, a blank
decorative hero waveform on some browsers, no URL import path, no playback
confirmation, and non-clickable history cards.

## Non-Goals

- No auth or user accounts.
- No permanent audio storage.
- No historical audio replay after reload.
- No guaranteed YouTube support for every video.
- No support for Spotify or platform pages that cannot produce audio bytes.

## Proposed Approach

Add a backend reference-audio import service that validates HTTP(S) URLs,
rejects local/private targets, streams direct audio with a 30 MB cap, and uses a
pinned `yt-dlp` adapter for best-effort YouTube extraction. Add metadata-only
delete endpoints for saved evaluations. Redesign the frontend around separate
reference and performance audio objects with object URLs, tabs, playback, trim
validation, recording duration controls, overwrite confirmation, and history
details in a modal.

## Data Flow

Reference upload or URL -> browser playable audio object -> evaluation form data
-> backend deterministic scoring -> optional Gemini explanation -> persisted
metadata -> history card -> detail modal or deletion.

## Files Expected to Change

- Backend API, settings, DB, import service, tests, and pinned dependencies.
- Frontend app, API helpers, types, styles, and tests.
- Env examples, Docker Compose, docs/API/README, and smoke/check scripts if needed.

## Milestones

1. Backend import/delete vertical slice with tests.
2. Frontend source-selection/playback/trim redesign with tests.
3. History detail/delete/clear-all UI with tests.
4. Docs/runtime updates and full validation.
5. Move plan to `plans/done/` when complete.

## Progress

- [x] Confirm branch/worktree state before implementation.
- [x] Save approved ExecPlan.
- [x] Implement backend URL import and history deletion.
- [x] Implement frontend UX and history controls.
- [x] Update docs/runtime configuration.
- [x] Run validation and record results.

## Validation and Acceptance

- `uv run ruff format --check . ../scripts`
- `uv run ruff check . ../scripts`
- `uv run pytest`
- `npm.cmd run lint`
- `npm.cmd run typecheck`
- `npm.cmd test -- --run`
- `npm.cmd run build`
- Smoke flow still evaluates generated local audio.

## Fallback and Error Handling

Direct URL and YouTube import failures return structured errors and do not block
normal uploaded-audio evaluation. Oversize imports are rejected before permanent
storage. History deletion reports missing IDs. Recording overwrite requires
confirmation.

## Risks and Mitigations

- Risk: YouTube import can break or be slow on free hosting.
  Mitigation: label as best effort, pin `yt-dlp`, enforce timeout/size/no playlist, and test with mocks.
- Risk: Browser CORS blocks direct audio playback from arbitrary URLs.
  Mitigation: backend imports the bytes and frontend plays the returned blob.
- Risk: History expectations imply audio replay.
  Mitigation: only show stored result details and document no permanent audio storage.

## Surprises & Discoveries

- Observation: PyPI lists `yt-dlp 2026.7.4` and Python 3.14 classifier/support.
  Evidence: PyPI project page checked on 2026-07-09.
- Observation: Git Bash on Windows did not have `python` on PATH and bundled `curl`
  could not read multipart files from raw Bash temp paths.
  Evidence: `scripts/smoke.sh` failed at the multipart upload with `curl: (26)`
  until it used `uv` as a Python fallback and converted fixture paths with
  `cygpath`.
- Observation: Local Compose validation first reported `max_upload_bytes` as
  `15728640` because local environment or `.env` values take precedence over
  tracked defaults.
  Evidence: tracked `.env.example`, `backend/.env.example`, `docker-compose.yml`,
  docs, and backend settings all use `31457280`; rerunning Compose with an
  explicit shell override reported `31457280`.

## Decision Log

- Decision: Pin `yt-dlp==2026.7.4`.
  Rationale: It is the current PyPI release and supports Python 3.14.
  Date/Author: 2026-07-09 / Codex
- Decision: Keep URL tab title as `URL` and mention YouTube in helper copy.
  Rationale: Avoids overpromising while still exposing the requested path.
  Date/Author: 2026-07-09 / McloiGG and Codex

## Validation Results

- Backend format: `uv run ruff format --check . ../scripts` passed.
- Backend lint: `uv run ruff check . ../scripts` passed.
- Backend tests: `uv run pytest -p no:cacheprovider` passed, 15 tests.
- Frontend lint: `npm.cmd run lint` passed.
- Frontend typecheck: `npm.cmd run typecheck` passed.
- Frontend tests: `npm.cmd test -- --run` passed, 6 tests.
- Frontend build: `npm.cmd run build` passed.
- Native smoke: `scripts/smoke.sh` passed against a temporary local backend.
- Docker Compose runtime: `docker compose up --build -d` passed with backend and
  frontend containers, backend health reported the expected `31457280` byte
  limit when validated with MVP env overrides, frontend root responded on port
  `5173`, and `scripts/smoke.sh` passed against the Compose backend.
- Docker cleanup: validation Compose projects were shut down with `down -v`, and
  temporary `seekphony-validation-*` images were removed.
