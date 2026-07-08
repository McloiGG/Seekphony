from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "backend" / "pyproject.toml"

EXPECTED_RUNTIME = {
    "fastapi",
    "httpx2",
    "psycopg",
    "psycopg-binary",
    "python-multipart",
    "uvicorn",
}
EXPECTED_DEV = {"pytest", "ruff"}


def main() -> int:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    runtime = data["project"]["dependencies"]
    dev = data["dependency-groups"]["dev"]
    errors = []

    errors.extend(_validate_group(runtime, EXPECTED_RUNTIME, "project.dependencies"))
    errors.extend(_validate_group(dev, EXPECTED_DEV, "dependency-groups.dev"))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Python dependency pins are exact and expected.")
    return 0


def _validate_group(requirements: list[str], expected: set[str], group: str) -> list[str]:
    errors: list[str] = []
    names = {_name(requirement) for requirement in requirements}
    unexpected = names - expected
    missing = expected - names
    if unexpected:
        errors.append(f"{group} contains unexpected packages: {', '.join(sorted(unexpected))}.")
    if missing:
        errors.append(f"{group} is missing expected packages: {', '.join(sorted(missing))}.")
    for requirement in requirements:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+==[^=<>!~,\s]+", requirement):
            errors.append(f"{group} has a non-exact pin: {requirement}.")
    return errors


def _name(requirement: str) -> str:
    return requirement.split("==", maxsplit=1)[0].lower()


if __name__ == "__main__":
    raise SystemExit(main())
