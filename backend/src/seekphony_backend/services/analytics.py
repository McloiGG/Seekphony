from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from seekphony_backend.core.errors import AppError
from seekphony_backend.db import Database, utc_now, utc_now_iso
from seekphony_backend.schemas import (
    AnalyticsResponse,
    PlayStartResponse,
    PlayStopResponse,
    SongOut,
)
from seekphony_backend.services.catalog import CatalogService


class AnalyticsService:
    def __init__(self, db: Database, catalog: CatalogService) -> None:
        self.db = db
        self.catalog = catalog

    def start_session(self, song_id: int) -> PlayStartResponse:
        song = self.catalog.get_song(song_id)
        session_id = uuid4().hex
        started_at = utc_now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO play_sessions(id, song_id, started_at, status)
                VALUES (?, ?, ?, 'active')
                """,
                (session_id, song_id, started_at),
            )
        return PlayStartResponse(
            status="started",
            session_id=session_id,
            song=song,
            started_at=started_at,
        )

    def stop_session(self, session_id: str) -> PlayStopResponse:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM play_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                raise AppError(
                    404, "not_found", "Play session was not found.", {"session_id": session_id}
                )
            if row["status"] == "stopped":
                raise AppError(
                    409,
                    "validation_error",
                    "Play session is already stopped.",
                    {"session_id": session_id},
                )
            started = datetime.fromisoformat(row["started_at"])
            duration = max(1, int((utc_now() - started).total_seconds()))
            stopped_at = utc_now_iso()
            conn.execute(
                """
                UPDATE play_sessions
                SET stopped_at = ?, duration_seconds = ?, status = 'stopped'
                WHERE id = ?
                """,
                (stopped_at, duration, session_id),
            )
            self._increment_song(conn, int(row["song_id"]), duration)

        song = self.catalog.get_song(int(row["song_id"]))
        return PlayStopResponse(
            status="stopped",
            session_id=session_id,
            song=song,
            duration_seconds=duration,
        )

    def record_play_event(self, song_id: int, duration_seconds: int | None = None) -> SongOut:
        song = self.catalog.get_song(song_id)
        duration = duration_seconds or song.duration_seconds or 180
        with self.db.transaction() as conn:
            session_id = uuid4().hex
            now = datetime.now(UTC)
            started = now.isoformat()
            stopped = now.isoformat()
            conn.execute(
                """
                INSERT INTO play_sessions(
                    id, song_id, started_at, stopped_at, duration_seconds, status
                )
                VALUES (?, ?, ?, ?, ?, 'stopped')
                """,
                (session_id, song_id, started, stopped, duration),
            )
            self._increment_song(conn, song_id, duration)
        return self.catalog.get_song(song_id)

    def summary(self) -> AnalyticsResponse:
        with self.db.connect() as conn:
            top_rows = conn.execute(
                """
                SELECT * FROM songs
                ORDER BY play_count DESC, total_listen_seconds DESC, title COLLATE NOCASE
                LIMIT 5
                """
            ).fetchall()
            total = conn.execute(
                "SELECT COALESCE(SUM(total_listen_seconds), 0) FROM songs"
            ).fetchone()[0]
            sessions = conn.execute(
                """
                SELECT ps.*, s.title, s.artist
                FROM play_sessions ps
                JOIN songs s ON s.id = ps.song_id
                ORDER BY ps.started_at DESC
                LIMIT 10
                """
            ).fetchall()
            recognitions = conn.execute(
                """
                SELECT rh.*, s.title AS matched_title, s.artist AS matched_artist
                FROM recognition_history rh
                LEFT JOIN songs s ON s.id = rh.matched_song_id
                ORDER BY rh.created_at DESC
                LIMIT 10
                """
            ).fetchall()

        return AnalyticsResponse(
            status="ok",
            top_songs=[SongOut.model_validate(dict(row)) for row in top_rows],
            total_listening_seconds=int(total),
            total_listening_minutes=round(int(total) / 60, 2),
            recent_sessions=[dict(row) for row in sessions],
            recent_recognitions=[dict(row) for row in recognitions],
            last_recognized_song=self.catalog.get_last_recognized(),
        )

    @staticmethod
    def _increment_song(conn, song_id: int, duration_seconds: int) -> None:
        conn.execute(
            """
            UPDATE songs
            SET play_count = play_count + 1,
                total_listen_seconds = total_listen_seconds + ?
            WHERE id = ?
            """,
            (duration_seconds, song_id),
        )
