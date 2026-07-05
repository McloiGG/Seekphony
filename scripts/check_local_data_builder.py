"""Regression checks for the sanitized local-data builder."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_local_data.py"
SECRET_PATTERN = re.compile(
    r"(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|@)"
)
EXPECTED_COUNTS = {
    "users": 8,
    "collections": 4,
    "catalog_items": 120,
    "rag_queries": 24,
}
REQUIRED_FILES = {
    "users": "users.jsonl",
    "collections": "collections.jsonl",
    "catalog_items": "catalog_items.jsonl",
    "rag_queries": "rag_queries.jsonl",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise AssertionError(f"{path}:{line_number}: invalid JSON") from error
    return records


def assert_unique_ids(name: str, records: list[dict[str, Any]]) -> None:
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        raise AssertionError(f"{name} contains duplicate ids")
    if any(not item_id for item_id in ids):
        raise AssertionError(f"{name} contains blank ids")


def assert_no_sensitive_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if SECRET_PATTERN.search(text):
        raise AssertionError(f"{path.name} appears to contain sensitive text")


def run_builder(output: Path) -> None:
    command = [
        sys.executable,
        str(BUILDER),
        "--output",
        str(output),
        "--users",
        str(EXPECTED_COUNTS["users"]),
        "--collections",
        str(EXPECTED_COUNTS["collections"]),
        "--items",
        str(EXPECTED_COUNTS["catalog_items"]),
        "--queries",
        str(EXPECTED_COUNTS["rag_queries"]),
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def validate_output(output: Path) -> None:
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        raise AssertionError("manifest.json was not generated")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["counts"] != EXPECTED_COUNTS:
        raise AssertionError("manifest counts do not match requested counts")
    if manifest["sanitization"]["contains_real_user_data"] is not False:
        raise AssertionError("manifest must mark the dataset as synthetic")

    loaded: dict[str, list[dict[str, Any]]] = {}
    for name, filename in REQUIRED_FILES.items():
        path = output / filename
        if not path.exists():
            raise AssertionError(f"{filename} was not generated")
        assert_no_sensitive_text(path)
        loaded[name] = load_jsonl(path)
        if len(loaded[name]) != EXPECTED_COUNTS[name]:
            raise AssertionError(f"{filename} has an unexpected record count")
        assert_unique_ids(name, loaded[name])

    first_item = loaded["catalog_items"][0]
    if not first_item["source_uri"].startswith("synthetic://"):
        raise AssertionError("catalog source URIs must use the synthetic scheme")
    if not first_item["body"]:
        raise AssertionError("catalog items must include searchable body text")

    first_query = loaded["rag_queries"][0]
    if not first_query["expected_item_ids"]:
        raise AssertionError("RAG queries must include expected retrieval targets")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="seekphony-local-data-") as temp_dir:
        output = Path(temp_dir) / "dataset"
        run_builder(output)
        validate_output(output)

    print("Local data builder generated sanitized valid data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
