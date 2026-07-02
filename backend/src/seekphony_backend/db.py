from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seekphony_backend.core.config import Settings
from seekphony_backend.core.normalization import normalize_text, normalize_url

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    genre TEXT NOT NULL,
    duration_seconds INTEGER,
    source_url TEXT,
    file_sha256 TEXT,
    file_path TEXT,
    title_norm TEXT NOT NULL,
    artist_norm TEXT NOT NULL,
    play_count INTEGER NOT NULL DEFAULT 0,
    total_listen_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_title_artist
ON songs(title_norm, artist_norm);

CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_source_url
ON songs(source_url)
WHERE source_url IS NOT NULL AND source_url != '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_file_sha256
ON songs(file_sha256)
WHERE file_sha256 IS NOT NULL AND file_sha256 != '';

CREATE TABLE IF NOT EXISTS recognition_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    input_summary TEXT,
    extracted_title TEXT,
    extracted_artist TEXT,
    confidence REAL,
    matched_song_id INTEGER REFERENCES songs(id),
    fallback_used INTEGER NOT NULL DEFAULT 0,
    fallback_reason TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS play_sessions (
    id TEXT PRIMARY KEY,
    song_id INTEGER NOT NULL REFERENCES songs(id),
    started_at TEXT NOT NULL,
    stopped_at TEXT,
    duration_seconds INTEGER,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def connect(self) -> sqlite3.Connection:
        self.settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.settings.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        with self.transaction() as conn:
            conn.executescript(SCHEMA_SQL)
        self.seed_if_empty()

    def seed_if_empty(self) -> None:
        with self.transaction() as conn:
            count = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
            if count:
                return
            seed_path = self.settings.seed_path
            if not seed_path.exists():
                return
            for song in _load_seed(seed_path):
                conn.execute(
                    """
                    INSERT INTO songs (
                        title, artist, genre, duration_seconds, source_url, file_sha256,
                        file_path, title_norm, artist_norm, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        song["title"],
                        song["artist"],
                        song.get("genre") or "Unknown",
                        song.get("duration_seconds"),
                        normalize_url(song.get("source_url")),
                        song.get("file_sha256"),
                        song.get("file_path"),
                        normalize_text(song["title"]),
                        normalize_text(song["artist"]),
                        utc_now_iso(),
                    ),
                )


def _load_seed(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))
