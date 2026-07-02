from __future__ import annotations

import sqlite3
from typing import Any

from seekphony_backend.core.errors import AppError
from seekphony_backend.core.normalization import normalize_text, normalize_url
from seekphony_backend.db import Database, row_to_dict, utc_now_iso
from seekphony_backend.schemas import SongCreate, SongOut


class CatalogService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_songs(self) -> list[SongOut]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM songs ORDER BY title COLLATE NOCASE").fetchall()
        return [SongOut.model_validate(dict(row)) for row in rows]

    def get_song(self, song_id: int) -> SongOut:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        song = row_to_dict(row)
        if not song:
            raise AppError(404, "not_found", "Song was not found.", {"song_id": song_id})
        return SongOut.model_validate(song)

    def add_song(self, data: SongCreate) -> SongOut:
        normalized_url = normalize_url(data.source_url)
        duplicate = self.find_duplicate(
            title=data.title,
            artist=data.artist,
            source_url=normalized_url,
            file_sha256=data.file_sha256,
        )
        if duplicate:
            raise AppError(
                409,
                "duplicate_detected",
                "Duplication detected!",
                {"duplicate": duplicate.model_dump()},
            )

        with self.db.transaction() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO songs (
                        title, artist, genre, duration_seconds, source_url, file_sha256,
                        file_path, title_norm, artist_norm, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data.title,
                        data.artist,
                        data.genre,
                        data.duration_seconds,
                        normalized_url,
                        data.file_sha256,
                        data.file_path,
                        normalize_text(data.title),
                        normalize_text(data.artist),
                        utc_now_iso(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise AppError(
                    409,
                    "duplicate_detected",
                    "Duplication detected!",
                    {"reason": str(exc)},
                ) from exc
        return self.get_song(int(cursor.lastrowid))
    
    def delete_song(self, song_id: int) -> bool:
        """
        Deletes a song record permanently from the SQLite tracking catalog database.
        Returns True if a row was deleted, False otherwise.
        """
        # 1. Connect to your SQLite database
        # (If your class already has a shared connection pool, use self.get_db() or equivalent)
        import sqlite3
        from pathlib import Path
        
        db_path = Path("data/seekphony.sqlite3")
        if not db_path.exists():
            return False

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            # 2. Execute the raw SQL DELETE statement safely using parameter binding (?)
            cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
            
            # 3. Check if any row was actually affected/deleted
            rows_affected = cursor.rowcount
            
            # 4. Commit changes to save to your disk storage permanently
            conn.commit()
            
            return rows_affected > 0
            
        except sqlite3.Error as e:
            print(f"Database error while trying to execute track removal: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()

    def find_duplicate(
        self,
        *,
        title: str,
        artist: str,
        source_url: str | None = None,
        file_sha256: str | None = None,
    ) -> SongOut | None:
        title_norm = normalize_text(title)
        artist_norm = normalize_text(artist)
        query = "SELECT * FROM songs WHERE title_norm = ? AND artist_norm = ?"
        params: list[Any] = [title_norm, artist_norm]

        if source_url:
            query += " OR source_url = ?"
            params.append(source_url)
        if file_sha256:
            query += " OR file_sha256 = ?"
            params.append(file_sha256)

        with self.db.connect() as conn:
            row = conn.execute(query, params).fetchone()
        song = row_to_dict(row)
        return SongOut.model_validate(song) if song else None

    def set_last_recognized(self, song_id: int | None) -> None:
        if song_id is None:
            return
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO app_state(key, value, updated_at)
                VALUES ('last_recognized_song_id', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (str(song_id), utc_now_iso()),
            )

    def get_last_recognized(self) -> SongOut | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key = 'last_recognized_song_id'"
            ).fetchone()
        if not row:
            return None
        try:
            return self.get_song(int(row["value"]))
        except (AppError, ValueError):
            return None

    def record_recognition(
        self,
        *,
        query_type: str,
        provider: str,
        status: str,
        input_summary: str | None = None,
        extracted_title: str | None = None,
        extracted_artist: str | None = None,
        confidence: float | None = None,
        matched_song_id: int | None = None,
        fallback_used: bool = False,
        fallback_reason: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO recognition_history (
                    query_type, provider, status, input_summary, extracted_title,
                    extracted_artist, confidence, matched_song_id, fallback_used,
                    fallback_reason, error_code, error_message, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_type,
                    provider,
                    status,
                    input_summary,
                    extracted_title,
                    extracted_artist,
                    confidence,
                    matched_song_id,
                    int(fallback_used),
                    fallback_reason,
                    error_code,
                    error_message,
                    utc_now_iso(),
                ),
            )
