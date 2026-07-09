from __future__ import annotations

import asyncio
import ipaddress
import mimetypes
import posixpath
import socket
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from seekphony_backend.core.config import Settings
from seekphony_backend.core.errors import AppError

HostResolver = Callable[[str], list[ipaddress.IPv4Address | ipaddress.IPv6Address]]
ImportAdapter = Callable[[str], "ImportedReference"]

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

LOCAL_HOSTS = {"localhost", "localhost.localdomain"}

AUDIO_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
}

ALLOWED_MEDIA_TYPES = {
    "application/octet-stream",
    "audio/aac",
    "audio/flac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/wave",
    "audio/webm",
    "audio/x-m4a",
    "audio/x-wav",
    "video/mp4",
    "video/ogg",
    "video/webm",
}


@dataclass(frozen=True, slots=True)
class ImportedReference:
    content: bytes
    filename: str
    media_type: str
    source_type: str
    title: str

    @property
    def byte_size(self) -> int:
        return len(self.content)


class ReferenceImportService:
    def __init__(
        self,
        settings: Settings,
        *,
        resolver: HostResolver | None = None,
        direct_adapter: ImportAdapter | None = None,
        youtube_adapter: ImportAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.resolver = resolver or _resolve_host_ips
        self.direct_adapter = direct_adapter
        self.youtube_adapter = youtube_adapter

    async def import_url(self, raw_url: str) -> ImportedReference:
        parsed = validate_public_http_url(raw_url, self.resolver)
        if is_youtube_url(parsed):
            return await asyncio.to_thread(self._import_youtube, raw_url)
        return await asyncio.to_thread(self._import_direct, raw_url)

    def _import_direct(self, raw_url: str) -> ImportedReference:
        if self.direct_adapter:
            imported = self.direct_adapter(raw_url)
            _validate_imported_size(imported, self.settings.max_upload_bytes)
            return imported
        return _download_direct_url(
            raw_url,
            max_bytes=self.settings.max_upload_bytes,
            timeout_seconds=self.settings.provider_timeout_seconds,
            resolver=self.resolver,
        )

    def _import_youtube(self, raw_url: str) -> ImportedReference:
        if self.youtube_adapter:
            imported = self.youtube_adapter(raw_url)
            _validate_imported_size(imported, self.settings.max_upload_bytes)
            return imported
        return _download_youtube_url(
            raw_url,
            max_bytes=self.settings.max_upload_bytes,
            timeout_seconds=self.settings.provider_timeout_seconds,
        )


def validate_public_http_url(
    raw_url: str,
    resolver: HostResolver | None = None,
) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise AppError(
            422,
            "validation_error",
            "Reference URL must start with http:// or https://.",
        )
    if not parsed.hostname:
        raise AppError(422, "validation_error", "Reference URL must include a hostname.")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in LOCAL_HOSTS or hostname.endswith((".localhost", ".local")):
        raise AppError(422, "validation_error", "Local reference URLs are not allowed.")
    host_resolver = resolver or _resolve_host_ips
    try:
        addresses = host_resolver(hostname)
    except OSError as exc:
        raise AppError(
            422,
            "validation_error",
            "Reference URL hostname could not be resolved.",
            {"hostname": hostname},
        ) from exc
    if not addresses:
        raise AppError(
            422,
            "validation_error",
            "Reference URL hostname did not resolve to an address.",
            {"hostname": hostname},
        )
    for address in addresses:
        if not address.is_global:
            raise AppError(
                422,
                "validation_error",
                "Reference URL must not resolve to a local, private, or reserved address.",
                {"hostname": hostname, "address": str(address)},
            )
    return parsed


def is_youtube_url(parsed: urllib.parse.ParseResult) -> bool:
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return hostname in YOUTUBE_HOSTS or hostname.endswith(".youtube.com")


def _resolve_host_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return [ipaddress.ip_address(hostname)]
    except ValueError:
        pass
    results = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for result in results:
        address = result[4][0]
        parsed = ipaddress.ip_address(address)
        if parsed not in addresses:
            addresses.append(parsed)
    return addresses


def _download_direct_url(
    raw_url: str,
    *,
    max_bytes: int,
    timeout_seconds: float,
    resolver: HostResolver,
) -> ImportedReference:
    validate_public_http_url(raw_url, resolver)

    class RedirectValidator(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            validate_public_http_url(newurl, resolver)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    request = urllib.request.Request(
        raw_url,
        headers={"User-Agent": "Seekphony/0.1 reference-importer"},
        method="GET",
    )
    opener = urllib.request.build_opener(RedirectValidator)
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            validate_public_http_url(final_url, resolver)
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise _too_large(max_bytes)
            media_type = response.headers.get_content_type() or "application/octet-stream"
            filename = _filename_from_headers(response.headers.get("Content-Disposition"))
            if not filename:
                filename = _filename_from_url(final_url, media_type)
            _validate_media_type(media_type, filename)
            content = _read_limited(response, max_bytes)
    except AppError:
        raise
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        raise AppError(
            502,
            "reference_import_failed",
            "Reference URL could not be imported.",
            retryable=True,
            stage="direct_url",
        ) from exc
    return ImportedReference(
        content=content,
        filename=filename,
        media_type=media_type,
        source_type="direct_url",
        title=Path(filename).stem or "Imported reference",
    )


def _download_youtube_url(
    raw_url: str,
    *,
    max_bytes: int,
    timeout_seconds: float,
) -> ImportedReference:
    try:
        from yt_dlp import DownloadError, YoutubeDL
    except ImportError as exc:
        raise AppError(
            503,
            "reference_import_unavailable",
            "YouTube import is unavailable because yt-dlp is not installed.",
            provider="yt-dlp",
            stage="youtube",
        ) from exc

    try:
        with tempfile.TemporaryDirectory(prefix="seekphony-ytdlp-") as temp_dir:
            output_template = str(Path(temp_dir) / "%(title).80s-%(id)s.%(ext)s")

            def progress_hook(status: dict[str, object]) -> None:
                downloaded = status.get("downloaded_bytes")
                if isinstance(downloaded, int) and downloaded > max_bytes:
                    raise _YouTubeTooLarge("YouTube import exceeded the configured size limit.")

            options = {
                "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best",
                "noplaylist": True,
                "outtmpl": output_template,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": timeout_seconds,
                "retries": 1,
                "fragment_retries": 1,
                "max_filesize": max_bytes,
                "progress_hooks": [progress_hook],
            }
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(raw_url, download=False)
                if info and info.get("_type") in {"playlist", "multi_video"}:
                    raise AppError(
                        422,
                        "validation_error",
                        "Playlist URLs are not supported for reference import.",
                    )
                info = ydl.extract_info(raw_url, download=True)
            files = [path for path in Path(temp_dir).rglob("*") if path.is_file()]
            if not files:
                raise AppError(
                    502,
                    "reference_import_failed",
                    "YouTube import did not produce an audio file.",
                    retryable=True,
                    provider="yt-dlp",
                    stage="youtube",
                )
            file_path = max(files, key=lambda path: path.stat().st_size)
            if file_path.stat().st_size > max_bytes:
                raise _too_large(max_bytes)
            content = file_path.read_bytes()
            media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            _validate_media_type(media_type, file_path.name)
            title = str(info.get("title") if isinstance(info, dict) else "") or file_path.stem
            return ImportedReference(
                content=content,
                filename=_safe_filename(file_path.name),
                media_type=media_type,
                source_type="youtube",
                title=title,
            )
    except AppError:
        raise
    except _YouTubeTooLarge as exc:
        raise _too_large(max_bytes) from exc
    except DownloadError as exc:
        raise AppError(
            502,
            "reference_import_failed",
            "YouTube import failed. Try a direct audio URL or upload the file instead.",
            retryable=True,
            provider="yt-dlp",
            stage="youtube",
        ) from exc


def _validate_imported_size(imported: ImportedReference, max_bytes: int) -> None:
    if imported.byte_size > max_bytes:
        raise _too_large(max_bytes)


def _read_limited(response: object, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(1024 * 256)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise _too_large(max_bytes)
        chunks.append(chunk)
    if not chunks:
        raise AppError(422, "validation_error", "Imported reference audio is empty.")
    return b"".join(chunks)


def _validate_media_type(media_type: str, filename: str) -> None:
    normalized = media_type.split(";", 1)[0].lower()
    suffix = Path(filename).suffix.lower()
    if normalized.startswith(("audio/", "video/")):
        return
    if normalized in ALLOWED_MEDIA_TYPES and (not suffix or suffix in AUDIO_EXTENSIONS):
        return
    if suffix in AUDIO_EXTENSIONS:
        return
    raise AppError(
        422,
        "validation_error",
        "Reference URL did not return a supported audio file.",
        {"media_type": normalized, "filename": filename},
    )


def _filename_from_headers(content_disposition: str | None) -> str | None:
    if not content_disposition:
        return None
    for part in content_disposition.split(";"):
        key, separator, value = part.strip().partition("=")
        if not separator:
            continue
        normalized = key.lower()
        cleaned = value.strip().strip('"')
        if normalized == "filename*":
            _, _, encoded = cleaned.partition("''")
            return _safe_filename(urllib.parse.unquote(encoded or cleaned))
        if normalized == "filename":
            return _safe_filename(cleaned)
    return None


def _filename_from_url(raw_url: str, media_type: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    name = _safe_filename(urllib.parse.unquote(posixpath.basename(parsed.path)))
    if not name:
        name = "imported-reference"
    if not Path(name).suffix:
        extension = mimetypes.guess_extension(media_type.split(";", 1)[0].lower()) or ".audio"
        name = f"{name}{extension}"
    return name


def _safe_filename(value: str) -> str:
    name = Path(value.replace("\\", "/")).name.strip().strip(".")
    return name[:120]


def _too_large(max_bytes: int) -> AppError:
    return AppError(
        413,
        "file_too_large",
        "Imported reference audio exceeds the configured maximum size.",
        {"max_upload_bytes": max_bytes},
    )


class _YouTubeTooLarge(Exception):
    pass
