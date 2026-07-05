"""Build sanitized production-like local data for Seekphony."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".local_data" / "production_like"
LOCAL_DATA_ROOT = ROOT / ".local_data"
BASE_TIME = datetime(2025, 1, 1, tzinfo=UTC)
SCHEMA_VERSION = "2026-07-05.1"

CONTENT_TYPES = (
    "note",
    "document",
    "bookmark",
    "transcript",
    "image_caption",
    "email_export",
    "task",
    "snippet",
)
LANGUAGES = ("en", "ms", "id", "zh-latn")
VISIBILITIES = ("private", "workspace", "shared_link")
ROLES = ("owner", "admin", "editor", "viewer")
TAG_POOL = (
    "architecture",
    "assistant",
    "catalog",
    "deployment",
    "finance",
    "health",
    "indexing",
    "legal",
    "personal",
    "product",
    "research",
    "search",
    "support",
    "travel",
    "workflow",
)
QUERY_INTENTS = (
    "catalog_lookup",
    "summarize_collection",
    "compare_items",
    "trace_source",
    "filter_by_tag",
    "assistant_followup",
)
EDGE_CASE_TITLES = {
    0: "Untitled imported note",
    1: "Very long title " + "with repeated safe words " * 8,
    2: "Mixed CASE punctuation query target - v2.0",
    3: "Near duplicate catalog item",
    4: "Near duplicate catalog item copy",
    5: "Item with empty tag set",
    6: "Large body item",
    7: "Shared link visibility sample",
}


def timestamp(offset_days: int, offset_minutes: int = 0) -> str:
    value = BASE_TIME + timedelta(days=offset_days, minutes=offset_minutes)
    return value.isoformat().replace("+00:00", "Z")


def safe_output_path(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == ROOT:
        raise ValueError("refusing to write local data to repository root")
    return resolved


def reset_output(path: Path, force: bool) -> None:
    output = safe_output_path(path)
    if not output.exists():
        output.mkdir(parents=True)
        return

    if any(output.iterdir()):
        if not force:
            raise FileExistsError(
                f"{output} already contains files; pass --force to replace it"
            )

        local_root = LOCAL_DATA_ROOT.resolve()
        if local_root not in output.parents and output != local_root:
            raise ValueError("--force can only replace paths under .local_data")
        shutil.rmtree(output)

    output.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, sort_keys=True, ensure_ascii=True))
            file.write("\n")


def users(count: int) -> list[dict[str, Any]]:
    records = []
    for index in range(count):
        records.append(
            {
                "id": f"user_{index + 1:04d}",
                "display_label": f"Synthetic User {index + 1:04d}",
                "role": ROLES[index % len(ROLES)],
                "status": "active" if index % 17 else "disabled",
                "created_at": timestamp(index % 365),
            }
        )
    return records


def collections(count: int, user_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for index in range(count):
        owner = user_records[index % len(user_records)]
        records.append(
            {
                "id": f"collection_{index + 1:04d}",
                "owner_id": owner["id"],
                "name": f"Synthetic Collection {index + 1:04d}",
                "visibility": VISIBILITIES[index % len(VISIBILITIES)],
                "created_at": timestamp(index % 240),
            }
        )
    return records


def catalog_body(index: int, content_type: str, tags: list[str]) -> str:
    tag_text = ", ".join(tags) if tags else "no tags"
    base = (
        f"Synthetic {content_type} record {index + 1}. "
        f"It references safe catalog topics: {tag_text}. "
        "The content is generated only for local search, ranking, and RAG tests. "
    )
    if index == 6:
        return base * 80
    if index in {3, 4}:
        return (
            "Near duplicate safe body for ranking tie tests. "
            "It intentionally repeats catalog and search terms. "
        )
    return base * (1 + index % 4)


def catalog_items(
    count: int,
    rng: random.Random,
    user_records: list[dict[str, Any]],
    collection_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for index in range(count):
        content_type = CONTENT_TYPES[index % len(CONTENT_TYPES)]
        tag_count = 0 if index == 5 else 1 + index % 5
        tags = sorted(rng.sample(TAG_POOL, k=tag_count)) if tag_count else []
        title = EDGE_CASE_TITLES.get(
            index,
            f"Synthetic {content_type.replace('_', ' ')} {index + 1:07d}",
        )
        created_offset = index % 730
        updated_offset = created_offset + index % 30
        owner = user_records[index % len(user_records)]
        collection = collection_records[index % len(collection_records)]
        records.append(
            {
                "id": f"item_{index + 1:07d}",
                "owner_id": owner["id"],
                "collection_id": collection["id"],
                "content_type": content_type,
                "title": title[:220],
                "body": catalog_body(index, content_type, tags),
                "tags": tags,
                "language": LANGUAGES[index % len(LANGUAGES)],
                "visibility": VISIBILITIES[index % len(VISIBILITIES)],
                "source_uri": f"synthetic://seekphony/catalog/item_{index + 1:07d}",
                "created_at": timestamp(created_offset),
                "updated_at": timestamp(updated_offset, index % 1440),
                "token_estimate": 80 + len(tags) * 9 + index % 1200,
                "embedding_status": "ready" if index % 31 else "pending",
                "quality_score": round(0.55 + (index % 45) / 100, 2),
                "acl_roles": [owner["role"], "viewer"],
            }
        )
    return records


def rag_queries(
    count: int,
    rng: random.Random,
    user_records: list[dict[str, Any]],
    item_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for index in range(count):
        intent = QUERY_INTENTS[index % len(QUERY_INTENTS)]
        actor = user_records[index % len(user_records)]
        selected = rng.sample(item_records, k=min(3, len(item_records)))
        records.append(
            {
                "id": f"query_{index + 1:07d}",
                "actor_user_id": actor["id"],
                "query_text": (
                    f"Find synthetic catalog information for {intent} "
                    f"with tag {TAG_POOL[index % len(TAG_POOL)]}"
                ),
                "expected_intent": intent,
                "filters": {
                    "content_type": CONTENT_TYPES[index % len(CONTENT_TYPES)],
                    "visibility": VISIBILITIES[index % len(VISIBILITIES)],
                },
                "expected_item_ids": [item["id"] for item in selected],
                "safety_label": "benign",
                "created_at": timestamp(index % 90, index % 1440),
            }
        )
    return records


def manifest(args: argparse.Namespace, counts: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": args.profile,
        "seed": args.seed,
        "generated_at": timestamp(0),
        "counts": counts,
        "sanitization": {
            "source": "deterministic synthetic data only",
            "contains_real_user_data": False,
            "contains_api_keys_or_secrets": False,
            "source_uri_scheme": "synthetic://",
        },
        "production_like_settings": {
            "items": args.items,
            "queries": args.queries,
            "users": args.users,
            "collections": args.collections,
        },
    }


def build(args: argparse.Namespace) -> Path:
    output = safe_output_path(args.output)
    reset_output(output, force=args.force)
    rng = random.Random(args.seed)

    user_records = users(args.users)
    collection_records = collections(args.collections, user_records)
    item_records = catalog_items(
        count=args.items,
        rng=rng,
        user_records=user_records,
        collection_records=collection_records,
    )
    query_records = rag_queries(args.queries, rng, user_records, item_records)

    write_jsonl(output / "users.jsonl", user_records)
    write_jsonl(output / "collections.jsonl", collection_records)
    write_jsonl(output / "catalog_items.jsonl", item_records)
    write_jsonl(output / "rag_queries.jsonl", query_records)

    counts = {
        "users": len(user_records),
        "collections": len(collection_records),
        "catalog_items": len(item_records),
        "rag_queries": len(query_records),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest(args, counts), indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile", default="production-like")
    parser.add_argument("--seed", type=int, default=20260705)
    parser.add_argument("--users", type=int, default=120)
    parser.add_argument("--collections", type=int, default=48)
    parser.add_argument("--items", type=int, default=25000)
    parser.add_argument("--queries", type=int, default=2500)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if min(args.users, args.collections, args.items, args.queries) < 1:
        print("All generated record counts must be positive.", file=sys.stderr)
        return 2

    output = build(args)
    print(f"Wrote sanitized local data to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
