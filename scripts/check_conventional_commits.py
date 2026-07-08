from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    r"(\([A-Za-z0-9._/-]+\))?!?: .+"
)


def main() -> int:
    commits = _commits_to_check()
    if not commits:
        print("No commits found to validate.")
        return 0

    failures = []
    for sha in commits:
        message = _git(["log", "-1", "--format=%B", sha])
        subject = message.splitlines()[0] if message else ""
        if not PATTERN.fullmatch(subject):
            failures.append((sha[:12], subject))

    if failures:
        for sha, subject in failures:
            print(f"ERROR: commit {sha} is not Conventional Commits v1.0.0: {subject}")
        return 1

    print(f"Validated {len(commits)} conventional commit message(s).")
    return 0


def _commits_to_check() -> list[str]:
    commit_range = os.getenv("COMMIT_RANGE")
    if commit_range:
        return _rev_list(commit_range)

    github_base_ref = os.getenv("GITHUB_BASE_REF")
    if github_base_ref:
        commits = _rev_list(f"origin/{github_base_ref}..HEAD")
        if commits:
            return commits

    head = _git(["rev-parse", "HEAD"], required=False)
    return [head] if head else []


def _rev_list(commit_range: str) -> list[str]:
    output = _git(["rev-list", "--reverse", commit_range], required=False)
    return [line for line in output.splitlines() if line]


def _git(args: list[str], *, required: bool = True) -> str:
    command = ["git", "-c", f"safe.directory={ROOT}", *args]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        if required:
            raise RuntimeError(completed.stderr.strip())
        return ""
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
