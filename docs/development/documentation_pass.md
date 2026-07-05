# Documentation Pass Workflow

Use this workflow whenever a documentation pass is requested.

## Required Steps

1. Review the full current codebase, not only the files that seem related.
2. Inventory implementation facts that user-facing or developer-facing docs
   should describe.
3. Compare the implementation against all committed documentation.
4. Update stale, missing, or misleading documentation.
5. Verify the documentation changes with the repository checks available in the
   current environment.
6. Open a pull request with the documentation updates.

## Review Scope

The full-codebase review includes:

- Root project metadata and configuration.
- CI and local Git hook behavior.
- Python scripts and auto-discovered checks.
- Generated-data contracts and ignored local output.
- QA documentation.
- README and agent instructions.

## Verification

Run the strict aggregate check when the required local toolchain is available:

```powershell
python scripts/check_all.py
```

When the local machine cannot run Python `3.14.*`, `uv 0.8.*`, or Ruff
`0.15.*`, run the largest safe subset available and document skipped checks in
the PR:

```powershell
python scripts/check_all.py --skip-tool-versions --skip-commits --skip-ruff
```

Before opening the pull request, also check the staged diff:

```powershell
git diff --cached --check
```

## Pull Request Expectations

The PR should state:

- Which parts of the codebase were reviewed.
- Which documentation was stale and how it changed.
- Which checks were run.
- Which checks were skipped, if any, and why.
