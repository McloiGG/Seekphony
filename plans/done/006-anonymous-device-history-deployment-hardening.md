# ExecPlan: Anonymous Device History and Deployment Hardening

## Status

completed

## Purpose / Big Picture

Implement the no-auth deployment-safe path: per-browser guest history,
admin-only global cleanup, and Render-compatible backend port handling. This
avoids rushed full auth while preventing normal deployed users from viewing or
clearing each other's saved evaluations.

## Requirement Link

- Data component: evaluation metadata remains persisted while history is scoped
  to the anonymous browser/device identity that created it.
- AI component: Gemini explanation metadata remains stored with each evaluation.
- Frontend application: history controls clearly operate on the current
  browser/device only.
- Backend application: FastAPI routes enforce device-scoped history and
  admin-only global cleanup.
- Integration layer: runtime configuration documents admin cleanup secrets and
  Render port behavior.
- Validation/fallback: missing device headers and bad admin tokens return
  structured errors.

## Context and Orientation

The current implementation stores all evaluations in one shared table and
exposes a global `DELETE /api/v1/evaluations` endpoint. That is acceptable for a
single-machine MVP but risky for a deployed public demo because users can see
or clear each other's history.

The approved direction is anonymous per-browser history, not full
authentication.

## Non-Goals

- No signup, login, passwords, OAuth, JWTs, sessions, or user table.
- No permanent raw audio storage.
- No frontend access to the admin cleanup token.
- No guarantee that anonymous device IDs provide real identity security.

## Proposed Approach

The frontend generates a `seekphony_device_id` UUID in `localStorage` and sends
it as `X-Seekphony-Device-ID` on evaluation create/list/get/delete/clear
requests. The backend validates the header, hashes it, stores only
`device_id_hash`, and filters history operations by that hash.

Normal `DELETE /api/v1/evaluations` clears only the current browser/device
history. A new admin-only `DELETE /api/v1/admin/evaluations` route clears the
entire table when `X-Seekphony-Admin-Token` matches `SEEKPHONY_ADMIN_TOKEN`.

The database schema adds nullable `device_id_hash` and an index on
`(device_id_hash, created_at DESC)`. Legacy rows with no device hash are hidden
from normal device history and removable through admin cleanup.

The backend Docker command will respect `${PORT:-8000}` for Render.

## Files Expected to Change

- `backend/src/seekphony_backend/api.py`
- `backend/src/seekphony_backend/core/config.py`
- `backend/src/seekphony_backend/core/security.py`
- `backend/src/seekphony_backend/services/evaluations.py`
- `backend/src/seekphony_backend/db.py`
- `backend/src/seekphony_backend/schemas.py` if response models need admin or
  health config additions
- `backend/tests/test_api.py`
- `backend/tests/test_config.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `backend/Dockerfile`
- `.env.example`
- `backend/.env.example`
- `docker-compose.yml`
- `README.md`
- `docs/API_CONTRACT.md`

## Progress

- [x] Save approved ExecPlan
- [x] Implement backend device-scoped history and admin cleanup
- [x] Implement database schema migration
- [x] Implement frontend device header handling and copy changes
- [x] Update runtime/docs/tests
- [x] Run validation and record results
- [x] Move plan to `plans/done/`

## Validation and Acceptance

- `cd backend && uv run ruff format --check . ../scripts`
- `cd backend && uv run ruff check . ../scripts`
- `cd backend && uv run pytest`
- `cd frontend && npm run lint`
- `cd frontend && npm run typecheck`
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`

Acceptance criteria:

- Device A can create/list/get/delete/clear its own evaluations.
- Device B cannot list/get/delete Device A's evaluations.
- Clearing Device B history does not remove Device A history.
- Missing device headers return structured validation errors.
- Admin global clear rejects missing/wrong tokens and clears all devices with
  the correct token.
- SQLite migration works on a pre-existing database without `device_id_hash`.
- Frontend sends a stable anonymous device header on evaluation/history calls.
- Render can inject `PORT` without needing a Dockerfile edit.

## Fallback and Error Handling

- Health and reference import remain public and do not require device headers.
- Missing or malformed device IDs return `validation_error`.
- Missing or incorrect admin tokens return `forbidden`.
- Admin cleanup with no configured token returns `admin_disabled`.

## Risks and Mitigations

- Risk: Anonymous IDs are not real authentication.
  Mitigation: document them as per-browser history only and keep full auth out
  of scope.
- Risk: Existing deployed data lacks `device_id_hash`.
  Mitigation: add backward-compatible migration and hide legacy rows from
  normal device history.
- Risk: Admin cleanup token leaks if added to frontend.
  Mitigation: only configure it in backend/Render env; do not expose it through
  Vercel or browser code.

## Decision Log

- Decision: Use anonymous device IDs instead of full auth.
  Rationale: It fixes deployed shared-history behavior with less scope and risk
  before showcase deployment.
  Date/Author: 2026-07-10 / McloiGG + Codex

- Decision: Store only a hash of the browser-generated ID.
  Rationale: The backend can partition records without persisting the raw
  browser identifier.
  Date/Author: 2026-07-10 / Codex

## Validation Results

- Backend format: `ruff format --check . <repo>/scripts` passed.
- Backend lint: `ruff check . <repo>/scripts` passed.
- Backend tests: `uv run pytest` passed, 20 tests.
- Frontend lint: `npm.cmd run lint` passed.
- Frontend typecheck: `npm.cmd run typecheck` passed.
- Frontend tests: `npm.cmd test -- --run` passed, 9 tests.
- Frontend build: `npm.cmd run build` passed.
- Smoke script was updated for the device header but not run against a live
  backend in this turn.

## Surprises & Discoveries

- `uv` could not use its default cache/project environment in the sandbox, so
  validation used `UV_CACHE_DIR=.uv-cache` and `UV_PROJECT_ENVIRONMENT=.venv-codex`.
- PowerShell blocked `npm.ps1`; frontend validation used `npm.cmd`.
- Direct `pytest.exe` from the uv environment hit a Windows launcher permission
  issue, so backend tests were validated through `uv run pytest`.
