"""Fail CI when files appear to contain committed secrets."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
TEXT_EXTENSIONS = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}


PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"
    ),
    "aws access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b"),
    "openai key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "assigned secret": re.compile(
        r"\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*"
        r"['\"][^'\"\s]{12,}['\"]",
        re.IGNORECASE,
    ),
}


def should_scan(path: Path) -> bool:
    if EXCLUDED_DIRS.intersection(path.parts):
        return False
    if path.name in {".gitignore", ".python-version"}:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def scan_file(path: Path) -> list[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((line_number, label))
    return findings


def main() -> int:
    findings: list[tuple[Path, int, str]] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        for line_number, label in scan_file(path):
            findings.append((path, line_number, label))

    if findings:
        print("Potential committed secrets found:")
        for path, line_number, label in findings:
            relative_path = path.relative_to(ROOT)
            print(f"- {relative_path}:{line_number}: {label}")
        return 1

    print("No obvious committed secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
