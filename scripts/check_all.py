"""Run every repository quality check that can be discovered."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
AUTO_SCRIPT_PREFIXES = ("check_", "scan_")
SPECIAL_SCRIPT_NAMES = {
    "check_all.py",
    "check_conventional_commits.py",
    "check_tool_versions.py",
}
ZERO_SHA = "0000000000000000000000000000000000000000"


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def command_text(command: list[str]) -> str:
    return " ".join(command)


def github_commit_range() -> str | None:
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    github_sha = os.environ.get("GITHUB_SHA")

    if event_path is None:
        return github_sha

    path = Path(event_path)
    if not path.exists():
        return github_sha

    event = json.loads(path.read_text(encoding="utf-8"))
    if event_name == "pull_request":
        pull_request = event.get("pull_request", {})
        base_sha = pull_request.get("base", {}).get("sha")
        head_sha = pull_request.get("head", {}).get("sha")
        if base_sha and head_sha:
            return f"{base_sha}..{head_sha}"

    if event_name == "push":
        before_sha = event.get("before")
        after_sha = event.get("after") or github_sha
        if before_sha and after_sha and before_sha != ZERO_SHA:
            return f"{before_sha}..{after_sha}"
        return after_sha

    return github_sha


def discovered_script_checks(skip_tool_versions: bool) -> list[Check]:
    checks: list[Check] = []
    for script in sorted(SCRIPTS_DIR.glob("*.py")):
        if not script.name.startswith(AUTO_SCRIPT_PREFIXES):
            continue
        if script.name in SPECIAL_SCRIPT_NAMES:
            continue

        checks.append(
            Check(
                name=f"python:{script.stem}",
                command=[sys.executable, relative(script)],
            )
        )

    if not skip_tool_versions:
        tool_versions = SCRIPTS_DIR / "check_tool_versions.py"
        checks.insert(
            0,
            Check(
                name="python:check_tool_versions",
                command=[sys.executable, relative(tool_versions)],
            ),
        )

    return checks


def commit_check() -> Check | None:
    revision_range = github_commit_range()
    if revision_range is None:
        revision_range = "HEAD"

    script = SCRIPTS_DIR / "check_conventional_commits.py"
    return Check(
        name="python:check_conventional_commits",
        command=[sys.executable, relative(script), revision_range],
    )


def ruff_checks() -> list[Check]:
    return [
        Check(name="ruff:format", command=["ruff", "format", "--check", "."]),
        Check(name="ruff:lint", command=["ruff", "check", "."]),
    ]


def run_check(check: Check) -> int:
    in_github = os.environ.get("GITHUB_ACTIONS") == "true"
    if in_github:
        print(f"::group::{check.name}")

    print(f"$ {command_text(check.command)}", flush=True)
    completed = subprocess.run(check.command, cwd=ROOT, check=False)

    if in_github:
        print("::endgroup::")

    if completed.returncode == 0:
        print(f"PASS {check.name}", flush=True)
    else:
        print(f"FAIL {check.name} ({completed.returncode})", flush=True)
    return completed.returncode


def build_checks(args: argparse.Namespace) -> list[Check]:
    checks = discovered_script_checks(skip_tool_versions=args.skip_tool_versions)

    if not args.skip_commits:
        commit = commit_check()
        if commit is not None:
            checks.append(commit)

    if not args.skip_ruff:
        checks.extend(ruff_checks())

    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-commits", action="store_true")
    parser.add_argument("--skip-ruff", action="store_true")
    parser.add_argument("--skip-tool-versions", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    for check in build_checks(args):
        if run_check(check) != 0:
            failures.append(check.name)

    if failures:
        print("Failed checks:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
