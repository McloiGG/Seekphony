# AGENTS.md

## Purpose

This repository is a Week 4 Independent Project. The goal is to build a functional, testable, demo-ready web application that satisfies `REQUIREMENTS.md`.

Treat this repository as the system of record. If important project knowledge exists only in chat, summarize it into the appropriate repo document before relying on it for implementation.

## Source of Truth

Read these files before planning significant work:

* `REQUIREMENTS.md` - official project requirements and rubric
* `README.md` - project overview and setup
* `.agent/PLANS.md` - ExecPlan protocol
* `.agent/REVIEW.md` - review checklist, if present
* relevant files in `docs/`
* relevant source files for the requested task

Do not treat `AGENTS.md` as the full project manual. It is a map to the rest of the repo.

## Instruction Priority

When instructions conflict, follow this order:

1. McloiGG's latest explicit instruction
2. `REQUIREMENTS.md`
3. Approved ExecPlans in `plans/active/`
4. This `AGENTS.md`
5. Existing working code
6. Optional ideas, bonus features, or old assumptions

If a request conflicts with `REQUIREMENTS.md`, explain the conflict before changing files.

If an approved plan conflicts with `REQUIREMENTS.md`, pause and explain the issue before continuing.

## Harness Engineering Principles

Optimize the repository for agent legibility.

Prefer:

* short entry-point documents that link to deeper docs
* executable checks over vague instructions
* small verifiable milestones over large risky changes
* structured outputs over prose-only behavior
* explicit boundaries between data, AI, backend, frontend, and integration logic
* documentation updates when repeated mistakes happen

Do not solve repeated agent mistakes only by adding more prose to `AGENTS.md`. Prefer updating docs, scripts, tests, schemas, or validation checks.

## Project Requirements Summary

The system must include:

* data component
* AI component
* frontend application
* backend application
* integration layer

The system must:

* solve a real and clearly defined problem
* accept real user input
* process input through a data/AI pipeline
* return structured results
* handle invalid input and errors gracefully
* be functional, testable, and demo-ready
* separate data logic, AI logic, and application logic

The AI component must:

* do meaningful work beyond simple prompt-response
* include validation
* return structured output
* include fallback handling

## Technical Requirements

Use:

* Python 3.14.*
* uv 0.8.*
* ruff 0.15.*
* pinned dependency versions
* Conventional Commits v1.0.0

Do not:

* expose API keys or secrets
* add unused dependencies
* over-engineer infrastructure
* prioritize bonus features before mandatory features
* build a generic chatbot clone

Use `.env` for local secrets and `.env.example` for safe placeholders.

## Container Runtime Configuration

Every containerized service must be independently buildable, configurable, runnable, and testable. Docker Compose may be used for local orchestration and demos, but no service may depend on Docker Compose as its only way to run.

Each service should support these runtime modes where applicable:

* native/local run from its own service directory
* direct Docker run using `docker run --env-file`
* Docker Compose run using the root Compose configuration
* CI/deployment run using injected environment variables

Use this configuration pattern:

* root `.env.example` documents Compose-level configuration
* root `.env` is for local Compose use and must be ignored by Git
* each service may have its own `.env.example` for direct local or direct Docker runs
* each service may have its own `.env` for local-only service runs and must be ignored by Git
* Dockerfiles must not copy `.env` files
* Dockerfiles must not contain secrets
* runtime configuration belongs outside the image

Compose services may use explicit `environment:` mappings, optional `env_file:`, or both. Prefer explicit `environment:` mappings with safe defaults when the service should boot without a local `.env`. Do not require Compose `env_file:` unless the README clearly instructs users to create the file first.

Frontend environment variables exposed to browser code are public and must never contain secrets.

## Planning Workflow

For small, local changes, proceed directly after briefly identifying the intended change.

For complex work, use an ExecPlan as described in `.agent/PLANS.md`.

Complex work includes:

* new backend services
* AI matching logic
* data model changes
* frontend/backend integration
* database or catalog changes
* deployment
* Docker
* CI/CD
* authentication
* significant refactors
* multi-file feature work
* major documentation restructuring

## ExecPlan Lifecycle

When complex work begins:

1. Draft an ExecPlan.
2. Explain which part of `REQUIREMENTS.md` it supports.
3. List expected files to change.
4. Identify assumptions, risks, validation, and fallback behavior.
5. Wait for McloiGG's approval before implementation unless McloiGG explicitly says to proceed.

When McloiGG approves an ExecPlan:

1. Save or update the plan in `plans/active/`.
2. Mark the plan status as `approved` or `in_progress`.
3. Implement according to the plan.
4. Keep the plan updated as progress happens.
5. Record surprises, discoveries, and design decisions.
6. Update validation results after running checks.
7. When complete, move the plan to `plans/done/` and mark it `completed`.

Do not silently skip updating the plan for complex work.

## Implementation Rules

Keep logic modular.

Separate:

* API route logic
* data/catalog logic
* AI/matching logic
* frontend UI logic
* configuration logic

Do not place all logic directly in route handlers.

Validate input at boundaries.

Return structured JSON from backend APIs.

Do not hide errors with broad silent fallbacks.

Fallbacks must be visible and intentional.

## Validation Harness

Prefer executable verification.

Use the most relevant available checks:

* `uv run ruff check .`
* `uv run ruff format .`
* `uv run pytest`
* backend smoke checks
* frontend manual browser checks
* API endpoint checks
* demo-flow checks

If checks are missing, suggest adding scripts such as:

* `scripts/check.sh`
* `scripts/smoke.sh`
* `scripts/demo_seed.sh`

Do not claim a check passed unless it was actually run.

## Protected Files

Do not modify these files unless McloiGG explicitly asks:

* `AGENTS.md`
* `REQUIREMENTS.md`
* `.agent/PLANS.md`
* `.agent/REVIEW.md`
* `.env`

You may suggest changes to protected files using the format below.

## Suggested Instruction Update Format

If an instruction file should change, do not edit it directly. Respond with:

### Suggested Instruction Update

* File:
* Current issue:
* Suggested change:
* Why this is better:

Only apply the change after McloiGG confirms.

## Final Response After Work

After completing work, report:

1. Files changed
2. What was implemented
3. How it maps to `REQUIREMENTS.md`
4. Checks run and results
5. Known limitations
6. Suggested next step

## Plan Mode Behavior

For complex work, architecture changes, multi-file implementation, Docker/runtime changes, AI logic, data model changes, or API contract changes, Codex must use Plan mode behavior.

Use `.agent/PLANS.md` as the canonical detailed protocol for ExecPlans and planning interviews.

Before producing a final implementation plan, Codex must inspect the relevant repo files, docs, approved plans, and existing code. After that inspection, Codex should ask only material unresolved questions that affect implementation. Do not ask questions already answered by repository sources.

If no material questions remain, Codex should say so and proceed to summarize the confirmed decisions, assumptions, non-goals, risks, and acceptance criteria before producing the final plan.

Final plans should be suitable for the normal Codex "Yes, implement plan" approval flow. Do not assume that a custom approval phrase is required.
