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
python scripts/check_tool_versions.py
python scripts/check_pyproject_dependencies.py
python scripts/scan_secrets.py
ruff format --check .
ruff check .
```
