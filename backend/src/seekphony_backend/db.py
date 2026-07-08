from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from seekphony_backend.core.config import Settings

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    reference_filename TEXT NOT NULL,
    performance_filename TEXT NOT NULL,
    reference_sha256 TEXT NOT NULL,
    performance_sha256 TEXT NOT NULL,
    clip_start_seconds REAL NOT NULL,
    clip_duration_seconds REAL NOT NULL,
    performance_start_seconds REAL NOT NULL,
    overall_score REAL NOT NULL,
    pitch_score REAL NOT NULL,
    rhythm_score REAL NOT NULL,
    stability_score REAL NOT NULL,
    coverage_score REAL NOT NULL,
    audio_quality_score REAL NOT NULL,
    key_shift_semitones INTEGER,
    pitch_error_cents REAL,
    timing_offset_ms REAL,
    voiced_coverage REAL NOT NULL,
    confidence REAL NOT NULL,
    metrics_json TEXT NOT NULL,
    segments_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    explanation_status TEXT NOT NULL,
    explanation_error TEXT,
    explanation_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_evaluations_created_at
ON evaluations(created_at DESC);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id BIGSERIAL PRIMARY KEY,
    created_at TEXT NOT NULL,
    reference_filename TEXT NOT NULL,
    performance_filename TEXT NOT NULL,
    reference_sha256 TEXT NOT NULL,
    performance_sha256 TEXT NOT NULL,
    clip_start_seconds DOUBLE PRECISION NOT NULL,
    clip_duration_seconds DOUBLE PRECISION NOT NULL,
    performance_start_seconds DOUBLE PRECISION NOT NULL,
    overall_score DOUBLE PRECISION NOT NULL,
    pitch_score DOUBLE PRECISION NOT NULL,
    rhythm_score DOUBLE PRECISION NOT NULL,
    stability_score DOUBLE PRECISION NOT NULL,
    coverage_score DOUBLE PRECISION NOT NULL,
    audio_quality_score DOUBLE PRECISION NOT NULL,
    key_shift_semitones INTEGER,
    pitch_error_cents DOUBLE PRECISION,
    timing_offset_ms DOUBLE PRECISION,
    voiced_coverage DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    metrics_json TEXT NOT NULL,
    segments_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    explanation_status TEXT NOT NULL,
    explanation_error TEXT,
    explanation_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_evaluations_created_at
ON evaluations(created_at DESC);
"""

INSERT_COLUMNS = (
    "created_at",
    "reference_filename",
    "performance_filename",
    "reference_sha256",
    "performance_sha256",
    "clip_start_seconds",
    "clip_duration_seconds",
    "performance_start_seconds",
    "overall_score",
    "pitch_score",
    "rhythm_score",
    "stability_score",
    "coverage_score",
    "audio_quality_score",
    "key_shift_semitones",
    "pitch_error_cents",
    "timing_offset_ms",
    "voiced_coverage",
    "confidence",
    "metrics_json",
    "segments_json",
    "warnings_json",
    "explanation_status",
    "explanation_error",
    "explanation_json",
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def is_postgres(self) -> bool:
        return self.settings.database_kind == "postgres"

    def initialize(self) -> None:
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        if self.is_postgres:
            with self.postgres_transaction() as conn, conn.cursor() as cursor:
                cursor.execute(POSTGRES_SCHEMA)
            return
        self.settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.sqlite_transaction() as conn:
            conn.executescript(SQLITE_SCHEMA)

    def create_evaluation(self, data: dict[str, Any]) -> int:
        payload = _serialize_json_fields(data)
        if self.is_postgres:
            return self._create_postgres_evaluation(payload)
        return self._create_sqlite_evaluation(payload)

    def get_evaluation(self, evaluation_id: int) -> dict[str, Any] | None:
        if self.is_postgres:
            with self.postgres_transaction() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT * FROM evaluations WHERE id = %s", (evaluation_id,))
                row = cursor.fetchone()
            return _deserialize_row(row)

        with self.sqlite_transaction() as conn:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE id = ?",
                (evaluation_id,),
            ).fetchone()
        return _deserialize_row(dict(row)) if row else None

    def list_evaluations(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        if self.is_postgres:
            with self.postgres_transaction() as conn, conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM evaluations ORDER BY created_at DESC, id DESC LIMIT %s",
                    (safe_limit,),
                )
                rows = cursor.fetchall()
            return [_deserialize_row(row) for row in rows if row is not None]

        with self.sqlite_transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM evaluations ORDER BY created_at DESC, id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [_deserialize_row(dict(row)) for row in rows]

    def _create_sqlite_evaluation(self, payload: dict[str, Any]) -> int:
        placeholders = ", ".join("?" for _ in INSERT_COLUMNS)
        columns = ", ".join(INSERT_COLUMNS)
        values = tuple(payload[column] for column in INSERT_COLUMNS)
        with self.sqlite_transaction() as conn:
            cursor = conn.execute(
                f"INSERT INTO evaluations ({columns}) VALUES ({placeholders})",
                values,
            )
            return int(cursor.lastrowid)

    def _create_postgres_evaluation(self, payload: dict[str, Any]) -> int:
        placeholders = ", ".join("%s" for _ in INSERT_COLUMNS)
        columns = ", ".join(INSERT_COLUMNS)
        values = tuple(payload[column] for column in INSERT_COLUMNS)
        with self.postgres_transaction() as conn, conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO evaluations ({columns}) VALUES ({placeholders}) RETURNING id",
                values,
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Database did not return an evaluation id.")
        return int(row["id"] if isinstance(row, dict) else row[0])

    @contextmanager
    def sqlite_transaction(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.settings.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def postgres_transaction(self) -> Iterator[Any]:
        if not self.settings.database_url:
            raise RuntimeError("DATABASE_URL is required for Postgres connections.")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("Postgres support requires psycopg runtime dependencies.") from exc

        conn = psycopg.connect(self.settings.database_url, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _serialize_json_fields(data: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(data)
    for key in ("metrics_json", "segments_json", "warnings_json", "explanation_json"):
        value = serialized.get(key)
        if value is not None and not isinstance(value, str):
            serialized[key] = json.dumps(value, separators=(",", ":"), sort_keys=True)
    return serialized


def _deserialize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    parsed = dict(row)
    for key in ("metrics_json", "segments_json", "warnings_json", "explanation_json"):
        value = parsed.get(key)
        if isinstance(value, str) and value:
            parsed[key] = json.loads(value)
        elif value is None:
            parsed[key] = None
    return parsed
