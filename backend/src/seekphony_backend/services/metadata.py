from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

from seekphony_backend.core.normalization import normalize_url
from seekphony_backend.core.security import sha256_bytes
from seekphony_backend.schemas import ExtractedMetadata


class MetadataService:
    def extract_from_file(self, content: bytes, filename: str | None) -> ExtractedMetadata:
        file_hash = sha256_bytes(content)
        title, artist = _title_artist_from_filename(filename)

        try:
            from mutagen import File as MutagenFile  # type: ignore[import-not-found]

            audio = MutagenFile(BytesIO(content), easy=True)
            if audio:
                tags = audio.tags or {}
                title = _first(tags.get("title")) or title
                artist = _first(tags.get("artist")) or artist
                genre = _first(tags.get("genre"))
                duration = int(audio.info.length) if getattr(audio, "info", None) else None
                return ExtractedMetadata(
                    title=title,
                    artist=artist,
                    genre=genre,
                    duration_seconds=duration,
                    file_sha256=file_hash,
                    provider="mutagen",
                    confidence=75 if title else 35,
                    fallback_used=False,
                )
        except Exception:
            pass

        return ExtractedMetadata(
            title=title,
            artist=artist,
            file_sha256=file_hash,
            provider="filename_hash",
            confidence=35 if title else 20,
            fallback_used=True,
            fallback_reason="Audio tags were unavailable; metadata came from filename and SHA-256.",
        )

    async def extract_from_url(self, url: str) -> ExtractedMetadata:
        normalized = normalize_url(url) or url
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_extract_with_ytdlp, normalized),
                timeout=8,
            )
        except Exception:
            title, artist = _title_artist_from_url(normalized)
            return ExtractedMetadata(
                title=title,
                artist=artist,
                source_url=normalized,
                provider="url_parser",
                confidence=30 if title else 0,
                fallback_used=True,
                fallback_reason="Best-effort URL parsing used because rich URL extraction failed.",
            )


def _extract_with_ytdlp(url: str) -> ExtractedMetadata:
    from yt_dlp import YoutubeDL  # type: ignore[import-not-found]

    with YoutubeDL({"quiet": True, "skip_download": True, "noplaylist": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    title = info.get("track") or info.get("title")
    artist = info.get("artist") or info.get("uploader")
    duration = info.get("duration")
    return ExtractedMetadata(
        title=title,
        artist=artist,
        duration_seconds=int(duration) if duration else None,
        source_url=normalize_url(url),
        provider="yt_dlp",
        confidence=70 if title else 20,
        fallback_used=False,
    )


def _title_artist_from_filename(filename: str | None) -> tuple[str | None, str | None]:
    if not filename:
        return None, None
    stem = Path(filename).stem.replace("_", " ").strip()
    if " - " in stem:
        artist, title = stem.split(" - ", maxsplit=1)
        return title.strip() or None, artist.strip() or None
    return stem or None, None


def _title_artist_from_url(url: str) -> tuple[str | None, str | None]:
    split = urlsplit(url)
    stem = Path(unquote(split.path)).stem.replace("-", " ").replace("_", " ").strip()
    if not stem:
        return None, None
    return stem, None


def _first(value: object) -> str | None:
    if isinstance(value, list | tuple):
        return str(value[0]) if value else None
    if value is None:
        return None
    return str(value)
