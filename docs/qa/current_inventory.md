# QA Inventory And Blocked Handoff

Date: 2026-07-05

## Scope

The requested QA workflow was applied to the current repository state. This is a
fresh foundation repository containing CI, local hooks, check scripts, and
documentation workflow guidance. It does not yet contain a Python application
package, HTTP API, React frontend, database schema, route definitions, UI
components, or deployed environment configuration.

## Production-Like Local Data

Implemented a deterministic sanitized data builder:

```powershell
python scripts/build_local_data.py
```

Default output is ignored at `.local_data/production_like` and contains:

- `users.jsonl`: 120 synthetic users with roles.
- `collections.jsonl`: 48 synthetic catalog collections.
- `catalog_items.jsonl`: 25,000 synthetic catalog items.
- `rag_queries.jsonl`: 2,500 synthetic RAG/search queries.
- `manifest.json`: schema version, counts, seed, and sanitization metadata.

Acceptance criteria:

- Generated data is deterministic for a fixed seed.
- Generated data contains no real user data, API keys, tokens, emails, private
  keys, or production identifiers.
- Generated source URIs use `synthetic://`.
- Output is local-only and ignored by Git.
- The generator refuses to replace non-empty output without `--force`.
- `--force` only deletes paths under `.local_data`.

Risk-based edge cases covered by generated records:

- Empty tag set.
- Long title.
- Large body.
- Near-duplicate catalog items.
- Mixed-case and punctuation-heavy title.
- Multiple content types, languages, visibilities, and embedding states.
- Queries with filters and expected retrieval targets.

Regression coverage:

- `scripts/check_local_data_builder.py` builds a small temporary dataset and
  validates counts, JSONL parsing, uniqueness, sanitization, and required fields.
- The check is auto-discovered by `scripts/check_all.py`.

## Documentation Workflow

Documentation passes are now defined in
`docs/development/documentation_pass.md`. Each pass must review the full
codebase, update stale docs, verify the changes, and open a pull request.

## User-Facing Inventory

No user-facing product features are implemented yet.

| Category | Inventory | Current status |
| --- | --- | --- |
| Roles | None implemented in an auth system | Blocked |
| Routes | No API or frontend routes exist | Blocked |
| Buttons | No UI exists | Blocked |
| Inputs | No UI exists | Blocked |
| Modals | No UI exists | Blocked |
| States | No app state or UI state exists | Blocked |
| Workflows | No product workflows exist | Blocked |

Acceptance criterion for continuing product QA:

- A runnable local app exists with documented startup commands.
- A production-like local configuration exists and does not require secrets.
- Routes, roles, UI states, and workflows are discoverable from source or docs.
- Test accounts or synthetic auth states are available.

Finite edge-case set once features exist:

- Empty and maximum-length user input.
- Invalid, missing, duplicated, and stale identifiers.
- Unauthorized, unauthenticated, and wrong-role access.
- Loading, empty, success, validation-error, permission-error, network-error,
  timeout, retry, and partial-result states.
- Keyboard-only operation and focus return after modal close.
- Search miss, exact match, noisy match, duplicate result, and large result set.
- RAG no-context, conflicting context, unsafe prompt injection, and citation
  mismatch.

## Real-User Test Log

No browser or API real-user test could be executed because there is no runnable
app entrypoint.

Evidence:

- `rg --files --hidden -g '!.git'` lists only repository foundation files.
- No `package.json`, React source tree, Python app package, API router, database
  migration, or server entrypoint exists.

## Bug And Finding Log

| ID | Severity | Finding | Reproduction evidence | Status |
| --- | --- | --- | --- | --- |
| QA-001 | Blocker | Product QA cannot run because no app surface exists | File inventory shows no frontend, API, schema, or app entrypoint | Blocked |
| QA-002 | High | Production-like local data did not exist | No seed-data or local-data scripts existed before this pass | Fixed |
| QA-003 | Medium | Full local strict checks depend on missing local Python 3.14, Ruff, and uv 0.8 | Local PATH exposes no runnable Python and no Ruff; CI remains strict | Environment blocked |

## Shared Cause Review

The current blockers share one cause: this repository is still at foundation
stage. The quality gate exists, but the product surface, schema, and runtime
contract are not implemented yet. The coherent fix in this pass was to add a
sanitized data scaffold and regression coverage without inventing product routes
or UI behavior.

## Rerun Result

The inventory was rerun after adding the data scaffold. Data generation is now
covered by an automated check. Product QA remains blocked until an application
surface exists.
