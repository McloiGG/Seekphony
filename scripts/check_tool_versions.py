"""Verify CI is running the pinned Python, uv, and Ruff version lines."""

from __future__ import annotations

import re
import subprocess
import sys

EXPECTED_PYTHON = (3, 14)
EXPECTED_UV = (0, 8)
EXPECTED_RUFF = (0, 15)


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def parse_version(output: str) -> tuple[int, int, int]:
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", output)
    if match is None:
        raise ValueError(f"could not parse semantic version from: {output!r}")
    return tuple(int(part) for part in match.groups())


def require_major_minor(
    name: str,
    version: tuple[int, int, int],
    expected: tuple[int, int],
):
    actual = version[:2]
    if actual != expected:
        expected_text = ".".join(str(part) for part in expected)
        actual_text = ".".join(str(part) for part in version)
        raise SystemExit(f"{name} must be {expected_text}.*, got {actual_text}")


def main() -> int:
    python_version = sys.version_info[:3]
    require_major_minor("Python", python_version, EXPECTED_PYTHON)

    uv_version = parse_version(command_output(["uv", "--version"]))
    require_major_minor("uv", uv_version, EXPECTED_UV)

    ruff_version = parse_version(command_output(["ruff", "--version"]))
    require_major_minor("Ruff", ruff_version, EXPECTED_RUFF)

    print(
        "Verified Python "
        f"{python_version[0]}.{python_version[1]}.{python_version[2]}, "
        f"uv {uv_version[0]}.{uv_version[1]}.{uv_version[2]}, "
        f"Ruff {ruff_version[0]}.{ruff_version[1]}.{ruff_version[2]}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
