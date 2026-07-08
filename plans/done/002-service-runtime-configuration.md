# ExecPlan: Standalone Service Runtime Configuration

This ExecPlan follows `.agent/PLANS.md`.

## Status

completed

## Purpose / Big Picture

Make the repository's container runtime rules explicit and harden the current backend so it can run as a standalone service without depending on Docker Compose.

After this work, the backend can be run natively from its service directory, directly with `docker run --env-file`, through the root Compose file, or in CI/deployment with injected environment variables.

## Requirement Link

- Data component: runtime SQLite and uploaded files stay outside the image and persist in local/runtime storage.
- AI component: optional provider keys remain runtime configuration and are never baked into images.
- Frontend application: no frontend UI files are implemented; future frontend browser env vars are documented as public.
- Backend application: backend remains independently buildable, configurable, runnable, and testable.
- Integration layer: documents root Compose config, service env config, direct Docker runs, `.dockerignore`, and CI/deployment injection.
- Validation/fallback: checks verify local env files are ignored, safe examples are trackable, and Docker context excludes local runtime/secrets.
- Rubric category: maintainability, demo readiness, deployment clarity, and solution quality.

## Context and Orientation

The backend foundation is already implemented under `backend/` with `backend/Dockerfile`, a root `docker-compose.yml`, and a root `.env.example`.

Current gaps:

- No `backend/.env.example` exists for direct backend or direct Docker runs.
- No `.dockerignore` exists at the root build context.
- README documents native and Compose runs, but not direct Docker or CI/deployment env injection.
- Harness docs do not yet capture the global rule that each containerized service must run independently from Compose.
- Container runtime data currently uses `/app/data`; direct Docker requirements now prefer runtime SQLite/uploads under `/app/var` with a named volume.

## Non-Goals

- No frontend UI implementation.
- No new paid provider or secret requirement.
- No change to API behavior.
- No new database schema feature.
- No guarantee Docker validation can run in this sandbox if Docker is unavailable.

## Proposed Approach

Add a concise global container runtime principle to `AGENTS.md`, then add detailed runtime planning requirements to `.agent/PLANS.md`.

For the backend, add `backend/.env.example`, make local `.env` files ignored while safe examples stay trackable, create a root `.dockerignore`, document all supported runtime modes, and align container runtime storage to `/app/var`.

Runtime configuration priority will be:

1. explicitly injected environment variables
2. service-local `.env` for native backend runs
3. application defaults

Docker Compose uses an optional root `.env` `env_file:` plus explicit `environment:` mappings with safe defaults. Direct Docker uses `docker run --env-file backend/.env`. Dockerfiles will not copy `.env` files or contain secrets.

## Data Flow

Runtime config flow:

env injection or env file -> backend settings resolution -> SQLite/upload paths outside image -> FastAPI service starts

Direct Docker flow:

root build context -> `.dockerignore` excludes secrets/runtime files -> `backend/Dockerfile` builds image -> `docker run --env-file backend/.env --mount source=seekphony-backend-data,target=/app/var` runs service with persistent runtime data

## Files Expected to Change

- `AGENTS.md`
- `.agent/PLANS.md`
- `README.md`
- `.env.example`
- `.gitignore`
- `.dockerignore`
- `docker-compose.yml`
- `backend/.env.example`
- `backend/Dockerfile`
- `backend/src/seekphony_backend/core/config.py`
- `backend/tests/test_config.py`
- `scripts/check.sh`
- `plans/active/002-service-runtime-configuration.md`

## Milestones

1. Save this approved ExecPlan and mark implementation in progress.
2. Update harness docs with the global standalone-service runtime rule.
3. Add backend service env example and `.env` ignore behavior.
4. Add `.dockerignore` and align container runtime paths to `/app/var`.
5. Update README with native, direct Docker, Compose, and CI/deployment run modes.
6. Run validation and record results.

## Progress

- [x] Save approved ExecPlan
- [x] Update harness runtime rules
- [x] Add backend env example and ignore behavior
- [x] Add Docker context/runtime data safeguards
- [x] Update runtime documentation
- [x] Run validation and record results

## Validation and Acceptance

Run and record:

- `uv run --project backend ruff format --check .`
- `uv run --project backend ruff check .`
- `uv run --project backend pytest`

Manual/file checks:

- `backend/.env.example` is trackable.
- `backend/.env` is ignored.
- root `.env` is ignored.
- `.dockerignore` excludes local env files, caches, uploads, local databases, virtualenvs, and build artifacts.
- No Dockerfile copies `.env` files or contains secrets.

Docker checks when Docker is available:

- `docker build -f backend/Dockerfile -t seekphony-backend .`
- `docker run --env-file backend/.env --mount source=seekphony-backend-data,target=/app/var -p 8000:8000 seekphony-backend`
- `docker compose up --build backend`

Acceptance criteria:

- Every containerized service must be able to run without Compose as its only path.
- Backend supports native/local, direct Docker, Compose, and CI/deployment env injection.
- Runtime configuration belongs outside images.
- Direct Docker runtime SQLite/uploads persist through a named volume mounted at `/app/var`.
- No frontend UI files are modified.

## Fallback and Error Handling

- Backend still boots with application defaults when local env files are absent.
- Explicit environment variables override service `.env` defaults.
- Compose must boot without root `.env` when explicit `environment:` mappings provide safe defaults.
- Missing optional provider keys keep provider paths disabled or on local fallback.
- Docker validation may be recorded as not run if Docker is unavailable in the environment.

## Risks and Mitigations

- Risk: Local `.env` behavior may conflict with Compose `.env`.
  Mitigation: root `.env.example` is Compose-focused; `backend/.env.example` is service-focused; backend native loading only reads service `.env` by default.

- Risk: Runtime data accidentally enters Docker context.
  Mitigation: add `.dockerignore` entries for env files, caches, uploads, local DBs, virtualenvs, and build outputs.

- Risk: Container path changes break seed loading.
  Mitigation: keep immutable seed data at `/app/data/seeds` and runtime SQLite/uploads at `/app/var`.

## Surprises & Discoveries

- Observation:
  The repository did not have a root `.dockerignore`.
  Evidence:
  Local inspection returned `MISSING .dockerignore`.

- Observation:
  uv validation could not query the Python interpreter inside the sandbox.
  Evidence:
  `uv run ruff format --check .` initially failed with `Access is denied. (os error 5)` and passed when rerun with escalation.

- Observation:
  Docker is not available in this environment.
  Evidence:
  `docker --version` timed out, and `Get-Command docker` returned no command.

## Decision Log

- Decision:
  Track standalone runtime hardening as a new ExecPlan instead of reopening completed `001-backend-foundation`.
  Rationale:
  Keeps the completed backend foundation plan intact and makes this cross-service runtime principle explicit.
  Date/Author:
  2026-07-01 / McloiGG + Codex

- Decision:
  Backend container runtime state should live under `/app/var`.
  Rationale:
  Makes direct Docker named-volume usage clear while keeping seed data separate from runtime SQLite/uploads.
  Date/Author:
  2026-07-01 / Codex

- Decision:
  Native backend runs may load `backend/.env`, but injected environment variables take priority.
  Rationale:
  Supports service-local configuration without adding dependencies and keeps CI/deployment overrides predictable.
  Date/Author:
  2026-07-01 / Codex

- Decision:
  Compose may use explicit `environment:` mappings, optional `env_file:`, or both; the backend Compose service uses optional root `.env` plus explicit mappings with safe defaults.
  Rationale:
  Keeps Compose runnable without a local root `.env` while still allowing root `.env` interpolation for local overrides.
  Date/Author:
  2026-07-01 / McloiGG + Codex

## Validation Results

Validation run on 2026-07-01:

- `uv run ruff format --check .`: passed after running `uv run ruff format .` on two files.
- `uv run ruff check .`: passed.
- `uv run pytest`: passed, 9 tests.
- `git diff --check`: passed with line-ending warnings only.
- `git check-ignore -q .env`: passed, root `.env` is ignored.
- `git check-ignore -q backend/.env`: passed, `backend/.env` is ignored.
- `git status --short -- backend/.env.example`: confirmed `backend/.env.example` is trackable.
- Dockerfile env/secret copy check: passed; no `COPY`/`ADD` of `.env` and no secret literals found.
- Compose environment check: passed by inspection; `docker-compose.yml` uses optional `env_file:` with `required: false` plus explicit `environment:` mappings with safe defaults.
- README Compose docs check: passed after clarification; root `.env` is documented as optional.
- `.dockerignore` coverage check: passed for env files, caches, virtualenvs, uploads, local databases, runtime `var/`, and build artifacts.
- Docker build/direct run/Compose run: not run because Docker is unavailable in this environment.

## Outcomes & Retrospective

Completed standalone runtime hardening:

- Added global container runtime rules to `AGENTS.md`.
- Added detailed Docker/runtime planning requirements to `.agent/PLANS.md`.
- Added backend service env template and native service `.env` loading with injected env override behavior.
- Added root `.dockerignore`.
- Aligned container runtime SQLite/uploads to `/app/var`.
- Updated direct Docker, Compose, native, and CI/deployment documentation.
- Added optional Compose `env_file:` while keeping explicit `environment:` mappings with safe defaults.

Remaining follow-up:

- Run Docker build/direct-run/Compose validation on a machine with Docker installed.
