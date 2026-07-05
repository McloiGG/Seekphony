"""Validate commit subjects against Conventional Commits v1.0.0."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HEADER_PATTERN = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)"
    r"(?P<scope>\([A-Za-z0-9._/-]+\))?"
    r"(?P<breaking>!)?: "
    r"(?P<description>\S.*)$"
)


def run_git_log(revision_range: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "log", "--format=%H%x00%s", revision_range],
        check=True,
        capture_output=True,
        text=True,
    )

    commits: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        commit_hash, subject = line.split("\0", maxsplit=1)
        commits.append((commit_hash, subject))
    return commits


def subject_from_message_file(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        subject = line.strip()
        if subject and not subject.startswith("#"):
            return subject
    return ""


def validate_subject(subject: str) -> str | None:
    match = HEADER_PATTERN.match(subject)
    if match is None:
        return (
            "expected '<type>[optional scope][optional !]: <description>', "
            "for example 'feat(search): add catalog indexing'"
        )

    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "revision_range",
        nargs="?",
        help="Git revision or revision range to inspect",
    )
    parser.add_argument(
        "--message-file",
        type=Path,
        help="Commit message file to inspect from a commit-msg hook",
    )
    args = parser.parse_args()

    if args.message_file is not None:
        subject = subject_from_message_file(args.message_file)
        error = validate_subject(subject)
        if error is not None:
            print("Commit message must follow Conventional Commits v1.0.0.")
            print(f"- {subject!r} ({error})")
            return 1

        print("Commit message follows Conventional Commits v1.0.0.")
        return 0

    if args.revision_range is None:
        parser.error("revision_range is required unless --message-file is used")

    commits = run_git_log(args.revision_range)
    if not commits:
        print("No commits found to validate.")
        return 0

    failures = []
    for commit_hash, subject in commits:
        error = validate_subject(subject)
        if error is not None:
            failures.append((commit_hash, subject, error))

    if failures:
        print("Commit messages must follow Conventional Commits v1.0.0.")
        for commit_hash, subject, error in failures:
            print(f"- {commit_hash[:12]}: {subject!r} ({error})")
        return 1

    print(f"Validated {len(commits)} commit message(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
