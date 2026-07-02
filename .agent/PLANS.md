# ExecPlan Protocol

Use an ExecPlan for complex features, significant refactors, architecture changes, AI/data logic changes, deployment work, or multi-file implementation tasks.

An ExecPlan is a living implementation document. It must be self-contained enough that another developer or agent can continue the work without relying on chat history.

## Core Rules

Every ExecPlan must:

* connect to `REQUIREMENTS.md`
* describe the user-visible goal
* describe the technical approach
* identify affected files
* explain validation and fallback behavior
* include independently verifiable milestones
* maintain progress while work happens
* record surprises and discoveries
* record design decisions
* end with validation results and a retrospective

Do not use an ExecPlan as a vague brainstorm.

Do not implement complex work from a one-line plan.

## Container Runtime Planning

ExecPlans that add or change containerized services must keep every service runnable without Compose as the only path.

For each affected service, document the applicable runtime modes:

- native/local run from the service directory
- direct Docker run using `docker run --env-file`
- Docker Compose run through the root Compose configuration
- CI/deployment run using injected environment variables

Use this configuration pattern:

- root `.env.example` documents Compose-level configuration
- root `.env` is for local Compose use and must be ignored by Git
- service `.env.example` files document direct service-local or direct Docker configuration
- service `.env` files are local-only and must be ignored by Git
- Dockerfiles must not copy `.env` files or contain secrets
- runtime configuration belongs outside the image

Compose services may use explicit `environment:` mappings, optional `env_file:`, or both. Prefer explicit `environment:` mappings with safe defaults when the service should boot without a local `.env`. Do not require Compose `env_file:` unless the README clearly instructs users to create the file first.

Docker/runtime ExecPlans must include validation for:

- independent image build
- direct Docker run with an env file
- Compose run through the root Compose file
- CI/deployment environment-variable injection
- `.dockerignore` coverage for env files, caches, uploads, local databases, virtualenvs, and build artifacts

Frontend environment variables exposed to browser code are public and must not contain secrets.

## Location

Draft or approved plans live in:

`plans/active/`

Completed plans move to:

`plans/done/`

Use clear filenames:

* `plans/active/001-backend-foundation.md`
* `plans/active/002-ai-matching-service.md`
* `plans/active/003-frontend-dashboard.md`

## Required Sections

Each ExecPlan must use this structure:

```md
# ExecPlan: <short action-oriented title>

This ExecPlan follows `.agent/PLANS.md`.

## Status

draft | approved | in_progress | blocked | completed

## Purpose / Big Picture

Explain what will exist after this work and how the user can observe it working.

## Requirement Link

Explain how this supports `REQUIREMENTS.md`.

Cover any relevant items:

- Data component:
- AI component:
- Frontend application:
- Backend application:
- Integration layer:
- Validation/fallback:
- Rubric category:

## Context and Orientation

Describe the current state. Name relevant files and modules by path. Define any non-obvious terms.

## Non-Goals

List what this plan intentionally avoids to prevent scope creep.

## Proposed Approach

Explain the implementation approach in prose.

## Data Flow

Describe the flow:

input -> processing -> structured output -> user-facing result

## Files Expected to Change

List expected file paths.

## Milestones

Describe each milestone in prose. Each milestone must be independently verifiable.

## Progress

Use checkboxes. Every stopping point must update this section.

- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## Validation and Acceptance

List commands and manual checks.

Examples:

- `uv run ruff check .`
- `uv run ruff format .`
- `uv run pytest`
- backend API smoke test
- frontend demo-flow test

## Fallback and Error Handling

Describe invalid input handling, AI failure behavior, no-match behavior, duplicate handling, and user-facing error messages.

## Risks and Mitigations

Document risks and how they will be reduced.

## Surprises & Discoveries

Record unexpected behavior, bugs, tool limitations, or useful findings.

Use this format:

- Observation:
  Evidence:

## Decision Log

Record design decisions.

Use this format:

- Decision:
  Rationale:
  Date/Author:

## Validation Results

Record actual check results after implementation.

## Outcomes & Retrospective

Summarize what was achieved, what remains, and what should be improved next.
```

## Update Rules

When work begins, set status to `in_progress`.

When a milestone is completed, update `Progress`.

When implementation differs from the original plan, update `Decision Log`.

When unexpected behavior appears, update `Surprises & Discoveries`.

When checks are run, update `Validation Results`.

When work is complete, update `Outcomes & Retrospective`, set status to `completed`, and move the file from `plans/active/` to `plans/done/`.

## Approval Behavior

Before approval, an ExecPlan is a proposal.

After McloiGG approves an ExecPlan, it must be saved or updated in `plans/active/`.

Approval means:

plan approved -> plan saved -> implementation begins -> plan updated during work -> validation recorded -> plan completed

Do not treat an approved plan as temporary chat context.

## Backend-Only Plans

When McloiGG is working on backend-only tasks, ExecPlans must explicitly separate:

- backend responsibilities
- frontend contract expectations
- frontend non-goals

For backend-only tasks, do not implement frontend files unless explicitly requested.

Instead, update `docs/API_CONTRACT.md` with the response shapes the frontend partner should use.

## Team Roles

McloiGG is currently responsible for backend implementation.

Ridzuanbkr is currently responsible for frontend implementation.

Prioritize backend work for McloiGG:

- FastAPI backend
- data/catalog service
- AI matching service
- validation and fallback handling
- analytics API
- API contract documentation for Ridzuanbkr
- backend tests and smoke checks

Do not implement frontend UI unless McloiGG explicitly asks.

When frontend behavior matters, document the expected API response shape in `docs/API_CONTRACT.md` instead of building the frontend.

The backend must run independently without the frontend.

The frontend must be treated as an external API consumer.

## Planning Interview Protocol

Before finalizing an ExecPlan for complex work, Codex must complete a planning interview workflow.

The goal of the interview workflow is to remove implementation-affecting ambiguity before the plan reaches the Codex "Yes, implement plan" approval stage.

### Explore First

Before asking questions, Codex must inspect the relevant repository state. Use the available non-mutating tools to read or search:

- `AGENTS.md`
- `REQUIREMENTS.md`
- `.agent/PLANS.md`
- approved plans in `plans/active/`
- relevant docs in `docs/`
- relevant source files, schemas, config, tests, scripts, and Docker/runtime files

Do not ask questions that are already answered by those sources.

### Ask Only Material Questions

Codex must ask focused questions only when the answer materially affects implementation. Relevant topics may include:

- scope and non-goals
- ownership boundaries between McloiGG and Ridzuanbkr
- required runtime modes
- API contracts
- data storage choices
- AI/provider requirements
- fallback behavior
- Docker/container expectations
- validation commands
- demo acceptance criteria
- risks and trade-offs

Codex must not ask every possible question. Avoid generic questionnaires.

If a decision is low-risk, reversible, and consistent with existing repository patterns, Codex may state it as an assumption instead of asking.

If no material unresolved questions remain after inspection, Codex should explicitly say that no material questions remain instead of inventing questions.

### Summarize Before Final Plan

When the interview workflow is complete, Codex must summarize:

1. confirmed decisions
2. assumptions
3. non-goals
4. risks
5. acceptance criteria

Then Codex may produce the final ExecPlan for McloiGG to approve through the Codex "Yes, implement plan" action.

The final ExecPlan should include durable decisions and acceptance criteria, but it does not need to duplicate the entire chat interview transcript.
