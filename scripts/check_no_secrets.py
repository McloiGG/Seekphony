from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".agents",
    ".local_data",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "data",
    "dist",
    "node_modules",
    "var",
}
SKIP_FILES = {"package-lock.json", "uv.lock"}
PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(access_secret|api_key|secret_key)\s*=\s*['\"][^'\"\s]{12,}['\"]"),
    re.compile(
        r"(?i)^(GEMINI_API_KEY|GOOGLE_API_KEY|SEEKPHONY_ACRCLOUD_ACCESS_SECRET)=\S+", re.MULTILINE
    ),
]


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or _should_skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(str(path.relative_to(ROOT)))
                break

    if findings:
        for finding in findings:
            print(f"ERROR: potential secret in {finding}")
        return 1

    print("No obvious committed secrets found.")
    return 0


def _should_skip(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return True
    if path.name.startswith(".env") and path.name != ".env.example":
        return True
    return any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)


if __name__ == "__main__":
    raise SystemExit(main())
