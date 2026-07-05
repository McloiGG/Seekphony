# Seekphony

Seekphony is a fresh Python-first project for an open-ended personal catalog,
search, and RAG assistant product with a React frontend planned later.

## Development Baseline

- Python must be `3.14.*`.
- `uv` must be `0.8.*`; CI installs `uv==0.8.22`.
- Python formatting uses `ruff==0.15.20`.
- Commit messages must follow Conventional Commits v1.0.0.
- Runtime dependencies in `pyproject.toml` must be exact-pinned and used by
  source code unless they are OS-specific.
- Do not commit API keys, tokens, private keys, passwords, or other secrets.
- Deployment jobs should be added after a target environment exists; the
  current workflow is the required quality gate for any future deployment.

## Local Checks

After installing the required Python and uv versions:

```powershell
python -m pip install --disable-pip-version-check "uv==0.8.22"
uv pip install --system "ruff==0.15.20"
python scripts/check_all.py
```

The aggregate checker automatically runs future zero-argument scripts named
`scripts/check_*.py` or `scripts/scan_*.py`, plus the built-in Ruff format and
lint checks.

## Development Automation

Future Codex development prompts should follow the repo instructions in
`AGENTS.md` and run `python scripts/check_all.py` before reporting completion.

Install local Git hooks once per clone:

```powershell
.\scripts\install_hooks.ps1
```

On Unix-like shells, use `sh scripts/install_hooks.sh`.

The hooks run the checks available on the local machine before commits and
pushes, and validate the actual commit message. Missing local Python or Ruff
does not block commits; GitHub Actions remains the full strict gate for Python
`3.14.*`, `uv 0.8.*`, and `ruff 0.15.*`.
