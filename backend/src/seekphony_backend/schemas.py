from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SongBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    artist: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=100)
    duration_seconds: int | None = Field(default=None, ge=1, le=60 * 60)
    source_url: str | None = Field(default=None, max_length=1000)

    @field_validator("title", "artist", "genre", "source_url", mode="before")
    @classmethod
    def _strip_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SongCreate(SongBase):
    file_sha256: str | None = None
    file_path: str | None = None


class SongOut(SongBase):
    id: int
    play_count: int
    total_listen_seconds: int
    file_sha256: str | None = None
    file_path: str | None = None
    created_at: str


class Candidate(BaseModel):
    song: SongOut
    confidence: float = Field(ge=0, le=100)
    reason: str


class ProviderTrace(BaseModel):
    provider: str
    stage: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    retryable: bool = False
    error_code: str | None = None
    message: str | None = None


class ExtractedMetadata(BaseModel):
    title: str | None = None
    artist: str | None = None
    genre: str | None = None
    duration_seconds: int | None = None
    source_url: str | None = None
    file_sha256: str | None = None
    provider: str
    confidence: float = Field(default=0, ge=0, le=100)
    fallback_used: bool = False
    fallback_reason: str | None = None


class SearchTextRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped


class SearchResponse(BaseModel):
    status: Literal["found", "candidates", "not_found"]
    query_type: Literal["text", "audio"]
    provider: ProviderTrace
    extracted: ExtractedMetadata | None = None
    song: SongOut | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    message: str


class UrlExtractRequest(BaseModel):
    url: HttpUrl


class PlayStartRequest(BaseModel):
    song_id: int = Field(gt=0)


class PlayStartResponse(BaseModel):
    status: Literal["started"]
    session_id: str
    song: SongOut
    started_at: str


class PlayStopResponse(BaseModel):
    status: Literal["stopped"]
    session_id: str
    song: SongOut
    duration_seconds: int


class PlayEventRequest(BaseModel):
    song_id: int = Field(gt=0)
    duration_seconds: int | None = Field(default=None, ge=1, le=60 * 60)


class AddSongResponse(BaseModel):
    status: Literal["created"]
    song: SongOut


class DuplicateResponse(BaseModel):
    status: Literal["duplicate_detected"]
    message: str
    duplicate: SongOut | None = None


class AnalyticsResponse(BaseModel):
    status: Literal["ok"]
    top_songs: list[SongOut]
    total_listening_seconds: int
    total_listening_minutes: float
    recent_sessions: list[dict[str, Any]]
    recent_recognitions: list[dict[str, Any]]
    last_recognized_song: SongOut | None
