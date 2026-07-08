# ExecPlan: Build Humming SPA Runtime

This ExecPlan follows `.agent/PLANS.md`.

## Status

completed

## Purpose / Big Picture

Build Seekphony into a demo-ready humming detection SPA with a resilient browser UI,
stable backend API contracts, containerized frontend runtime, clear setup docs, and
CI checks.

After this work, a user can run the backend and frontend together with Docker Compose,
run either service individually, or open the SPA while the backend is unavailable and
still see a usable interface with readable error states.

## Requirement Link

- Data component: catalog, recognition history, play analytics, and metadata extraction remain backend-managed.
- AI component: Gemini remains server-side for structured metadata extraction; audio providers are optional and validated with fallback.
- Frontend application: React SPA accepts text, upload, and microphone input and renders structured search results.
- Backend application: FastAPI exposes canonical `/api/v1` routes plus compatibility aliases.
- Integration layer: environment variables, Docker, CI, checks, README, and runtime config are updated together.
- Validation/fallback: frontend handles invalid input, no match, provider failure, backend outage, and malformed responses without faking results.
- Rubric category: solution quality, technical implementation, usability, maintainability, and demo readiness.

## Context and Orientation

The repository currently has a backend foundation, a Bootstrap static prototype in
`Frontend/`, and runtime docs that say frontend files are not implemented. A partner
pull introduced route-level ACRCloud code in `backend/src/seekphony_backend/api.py`,
including hardcoded credentials and route behavior that no longer matches tests or
`docs/API_CONTRACT.md`.

Observed starting validation:

- `uv run ruff format --check .` would reformat `api.py`, `catalog.py`, and `update_db.py`.
- `uv run ruff check .` fails mainly in `api.py` and `update_db.py`.
- `uv run pytest` fails 7 tests because canonical/alias routes are missing or route handlers call services incorrectly.
- Docker is not available locally.
- `gh` is not installed locally.
- Global `uv` is `0.11.20`; CI and containers must use `uv==0.8.22`.

## Non-Goals

- Do not call Gemini from browser code.
- Do not commit or expose provider credentials.
- Do not fake successful detection results when the backend is unavailable.
- Do not add authentication, multi-user state, or deployment hosting.
- Do not edit protected instruction files.

## Proposed Approach

First restore the backend API to thin route handlers that delegate to services. Move
ACRCloud recognition into an optional provider configured only by environment
variables. Add deterministic confidence analysis to search responses so the frontend
can visualize results without inventing data.

Then replace the static frontend prototype with a React + TypeScript + Vite SPA in
the existing `Frontend/` folder. The UI will use a dark, centered, music-recognition
hero inspired by SongFinder, plus an in-page detection workspace with text search,
audio upload, microphone recording, catalog summary, analytics summary, result
states, candidates, and confidence scoring.

Finally, add frontend Docker support, root checks, GitHub Actions, env examples, and
README/API docs that reflect the current implementation.

## Data Flow

Text search:

user text -> frontend validation -> `POST /api/v1/search/text` -> Gemini provider if configured -> local extraction fallback -> matcher -> structured response with optional analysis -> frontend result and analytics display

Audio search:

upload or microphone blob -> frontend validation -> `POST /api/v1/search/audio` -> optional ACRCloud provider if configured -> optional Shazamio provider if enabled -> local filename/hash fallback -> matcher -> structured response with optional analysis -> frontend result and analytics display

Runtime config:

local Vite env or container public config -> frontend API client -> backend URL -> readable success/error UI

## Files Expected to Change

- `backend/src/seekphony_backend/`
- `backend/tests/`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `Frontend/`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`
- `.github/workflows/ci.yml`
- `scripts/`
- `docs/`
- `README.md`
- `plans/active/003-humming-spa-runtime.md`

## Milestones

1. Save this approved ExecPlan and mark it in progress.
2. Restore backend routes and provider boundaries.
3. Add confidence analysis and backend regression tests.
4. Replace static frontend with React/Vite SPA.
5. Add frontend tests, Docker runtime, env examples, and root checks.
6. Update README and API/architecture docs.
7. Run backend, frontend, full-loop, and browser validation.
8. Move this plan to `plans/done/` with validation results.
9. Commit, push, and open a draft PR if available.

## Progress

- [x] Save approved ExecPlan
- [x] Restore backend routes and provider boundaries
- [x] Add confidence analysis and backend regression tests
- [x] Replace static frontend with React/Vite SPA
- [x] Add frontend tests, Docker runtime, env examples, and root checks
- [x] Update README and API/architecture docs
- [x] Run validation and browser checks
- [x] Move plan to done
- [ ] Commit, push, and open draft PR if possible
  - Blocked in this environment: staging requires writing `.git/index.lock`, and the sandbox escalation was rejected by the usage-limit gate.

## Validation and Acceptance

Run and record:

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- `npm.cmd ci`
- `npm.cmd run lint`
- `npm.cmd run typecheck`
- `npm.cmd test -- --run`
- `npm.cmd run build`
- `scripts/check.sh`
- browser check against the local frontend

Docker checks when Docker is available:

- `docker build -f backend/Dockerfile -t seekphony-backend .`
- `docker build -f Frontend/Dockerfile -t seekphony-frontend .`
- `docker compose up --build`
- frontend remains reachable when backend is stopped

Acceptance criteria:

- No hardcoded API keys or provider secrets remain in tracked code.
- Backend tests pass under Python 3.14.
- Frontend builds and tests with pinned dependencies.
- SPA shows readable success, empty, validation, provider, and backend-down states.
- Frontend container can be built and run independently from Compose.
- README documents Compose, native, and direct Docker workflows.
- CI checks Conventional Commits, tool versions, dependencies, backend, frontend, and secret safety.

## Fallback and Error Handling

- Missing Gemini key uses local structured extraction fallback.
- Missing ACRCloud credentials skip ACRCloud and use Shazamio/local fallback.
- Missing Shazamio or provider failure uses filename/hash fallback.
- No match returns `not_found` or candidates rather than a fake result.
- Backend outage shows a readable frontend error and retry action.
- Microphone denial, empty text, oversized upload, malformed JSON, and timeout stay in UI state without app crashes.

## Risks and Mitigations

- Risk: local `uv` version is not 0.8.*.
  Mitigation: CI and Docker pin `uv==0.8.22`; local tool-version check records the mismatch.

- Risk: Docker cannot be run locally.
  Mitigation: add Docker files and exact commands, then record Docker validation as blocked if still unavailable.

- Risk: ACRCloud credentials may already be leaked.
  Mitigation: remove them from tracked files and explicitly report that real keys must be rotated.

- Risk: frontend dependency installation may require network.
  Mitigation: pin exact versions and commit `package-lock.json`.

## Surprises & Discoveries

- Observation:
  Current `api.py` has hardcoded ACRCloud credentials and route-level provider logic.
  Evidence:
  Local inspection of `backend/src/seekphony_backend/api.py`.

- Observation:
  Tests encode the newer API contract, while current routes are older.
  Evidence:
  `uv run pytest` failed 7 tests for missing routes and incorrect service calls.

- Observation:
  Git requires a per-command `safe.directory` override in this workspace.
  Evidence:
  Plain `git status` fails with a dubious ownership warning.

## Decision Log

- Decision:
  Keep the existing `Frontend/` directory name.
  Rationale:
  Avoids Windows case-only rename churn and preserves existing repository structure.
  Date/Author:
  2026-07-07 / McloiGG + Codex

- Decision:
  Gemini is server-side only.
  Rationale:
  Browser-exposed provider keys would violate the no-secrets requirement.
  Date/Author:
  2026-07-07 / McloiGG + Codex

- Decision:
  ACRCloud is optional and env-backed.
  Rationale:
  Preserves partner humming work without committing secrets or making tests network-dependent.
  Date/Author:
  2026-07-07 / McloiGG + Codex

## Validation Results

- Backend:
  - `uv run ruff format . ../scripts`: passed.
  - `uv run ruff check . ../scripts`: passed.
  - `uv run pytest`: passed, 9 tests.
- Frontend:
  - `npm.cmd ci`: passed.
  - `npm.cmd run lint`: passed.
  - `npm.cmd run typecheck`: passed.
  - `npm.cmd test -- --run`: passed, 3 tests.
  - `npm.cmd run build`: passed.
- Repository policy:
  - `check_pyproject_dependencies.py`: passed.
  - `check_no_secrets.py`: passed after excluding ignored local `.env` files.
  - `check_conventional_commits.py`: passed for current HEAD.
  - `check_tool_versions.py`: blocked locally because global uv is `0.11.20`, not `0.8.*`.
- Root check:
  - `bash scripts/check.sh`: reached the tool-version gate and stopped on local uv `0.11.20`.
- Browser:
  - Desktop SPA loaded at `http://127.0.0.1:5173/`, hero rendered, backend connected, no local console errors.
  - Text search returned "Blinding Lights" with confidence analytics, no local console errors.
  - Backend-down reload kept the SPA usable and showed a readable offline state, no local console errors.
  - Mobile viewport had no detected horizontal overflow and no local console errors.
- Docker:
  - Not run because Docker is not installed or not on PATH in this environment.

## Outcomes & Retrospective

Completed:

- Restored backend API routes and service delegation.
- Removed hardcoded ACRCloud credentials and replaced them with optional env-backed provider settings.
- Added structured confidence analysis to search responses.
- Replaced the Bootstrap prototype with a React + TypeScript + Vite SPA.
- Added frontend tests, Dockerfile, Nginx runtime config, Compose frontend service, env examples, CI, and repository policy scripts.
- Updated README, architecture docs, and API contract to reflect the current implementation.

Remaining:

- Stage, commit, push, and open the draft PR from an environment with Git metadata write access.
- Install or switch local `uv` to `0.8.*` for the full root loop to pass locally.
- Install Docker to run direct image and Compose validation.
- Rotate any real ACRCloud keys that were previously committed before this cleanup.
