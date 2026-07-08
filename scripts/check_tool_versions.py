from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []

    if sys.version_info[:2] != (3, 14):
        errors.append(f"Python must be 3.14.*; current interpreter is {sys.version.split()[0]}.")

    uv_output = _run(["uv", "--version"])
    if uv_output is None:
        errors.append("uv is not available on PATH.")
    elif not re.search(r"\b0\.8\.\d+\b", uv_output):
        errors.append(f"uv must be 0.8.*; current output is {uv_output!r}.")

    ruff_output = _run(["uv", "run", "--project", "backend", "ruff", "--version"])
    if ruff_output is None:
        errors.append("ruff could not be executed through uv.")
    elif not re.search(r"\b0\.15\.\d+\b", ruff_output):
        errors.append(f"ruff must be 0.15.*; current output is {ruff_output!r}.")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Tool versions are valid.")
    return 0


def _run(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
