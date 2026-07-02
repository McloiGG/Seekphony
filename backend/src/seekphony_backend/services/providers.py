from __future__ import annotations

import asyncio
import json
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from seekphony_backend.core.config import Settings
from seekphony_backend.schemas import ExtractedMetadata, ProviderTrace


@dataclass(slots=True)
class ProviderFailure(Exception):
    code: str
    message: str
    provider: str
    stage: str
    retryable: bool = False


class LocalTextProvider:
    name = "local_text_extractor"

    def extract(self, query: str) -> ExtractedMetadata:
        title: str | None = None
        artist: str | None = None
        cleaned = query.strip()
        lowered = cleaned.lower()

        if " by " in lowered:
            parts = cleaned.split(" by ", maxsplit=1)
            if len(parts) == 2:
                title, artist = parts[0].strip(" \"'"), parts[1].strip(" \"'")
        elif " - " in cleaned:
            left, right = cleaned.split(" - ", maxsplit=1)
            artist, title = left.strip(), right.strip()
        elif '"' in cleaned:
            fragments = [part.strip() for part in cleaned.split('"') if part.strip()]
            if fragments:
                title = fragments[0]

        if not title:
            title = cleaned

        return ExtractedMetadata(
            title=title,
            artist=artist,
            provider=self.name,
            confidence=55 if artist else 45,
            fallback_used=True,
            fallback_reason=(
                "Local extraction used because no external text provider returned metadata."
            ),
        )


class GeminiTextProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(self, query: str) -> ExtractedMetadata:
        if not self.settings.gemini_api_key:
            raise ProviderFailure(
                "provider_unavailable",
                "Gemini API key is not configured.",
                self.name,
                "text_extraction",
                retryable=False,
            )
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._extract_sync, query),
                timeout=self.settings.provider_timeout_seconds,
            )
        except TimeoutError as exc:
            raise ProviderFailure(
                "provider_timeout",
                "Gemini text extraction timed out.",
                self.name,
                "text_extraction",
                retryable=True,
            ) from exc

    def _extract_sync(self, query: str) -> ExtractedMetadata:
        prompt = (
            "Extract possible song metadata from this user search. "
            "Return strict JSON with keys title, artist, genre, confidence. "
            "Use null when unknown. Query: "
            f"{query!r}"
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent?key={self.settings.gemini_api_key}"
        )
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310 - user-configured Gemini endpoint.
                request,
                timeout=self.settings.provider_timeout_seconds,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderFailure(
                "provider_unavailable",
                f"Gemini request failed: {exc.reason}",
                self.name,
                "text_extraction",
                retryable=True,
            ) from exc

        text = _gemini_text(response_payload)
        try:
            payload = json.loads(_json_object(text))
        except json.JSONDecodeError as exc:
            raise ProviderFailure(
                "invalid_provider_output",
                "Gemini returned non-JSON metadata.",
                self.name,
                "text_extraction",
            ) from exc

        # Replace the crashing line with a safe float conversion block
        raw_confidence = payload.get("confidence")
        try:
            # If it's already a number or numeric string, convert it cleanly
            confidence_value = float(raw_confidence) if raw_confidence is not None else 70.0
        except ValueError:
            # If the AI returns strings like 'high', 'medium', or 'low', assign fallback numbers
            mapping = {"high": 90.0, "medium": 70.0, "low": 40.0}
            confidence_value = mapping.get(str(raw_confidence).lower().strip(), 70.0)

        return ExtractedMetadata(
            title=payload.get("title") or None,
            artist=payload.get("artist") or None,
            genre=payload.get("genre") or None,
            duration_seconds=payload.get("duration_seconds") or None,
            source_url=payload.get("source_url") or None,
            provider=self.name,
            confidence=confidence_value,  # Use the safely checked value here
            fallback_used=False,
        )


class ShazamioAudioProvider:
    name = "shazamio"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def recognize(self, content: bytes, filename: str | None) -> ExtractedMetadata:
        if not self.settings.enable_shazamio:
            raise ProviderFailure(
                "provider_unavailable",
                "Shazamio provider is disabled.",
                self.name,
                "audio_recognition",
            )

        try:
            from shazamio import Shazam  # type: ignore[import-not-found]
        except Exception as exc:
            raise ProviderFailure(
                "provider_unavailable",
                "shazamio is not installed.",
                self.name,
                "audio_recognition",
            ) from exc

        suffix = Path(filename or "audio.bin").suffix or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
            temp.write(content)
            temp_path = Path(temp.name)

        try:
            last_error: Exception | None = None
            for attempt in range(self.settings.provider_retry_count + 1):
                try:
                    result = await asyncio.wait_for(
                        Shazam().recognize(str(temp_path)),
                        timeout=self.settings.provider_timeout_seconds,
                    )
                    track = result.get("track") if isinstance(result, dict) else None
                    if not track:
                        raise ProviderFailure(
                            "not_found",
                            "Shazamio did not identify a track.",
                            self.name,
                            "audio_recognition",
                            retryable=False,
                        )
                    return ExtractedMetadata(
                        title=track.get("title"),
                        artist=track.get("subtitle"),
                        provider=self.name,
                        confidence=90,
                        fallback_used=False,
                    )
                except Exception as exc:  # noqa: BLE001 - provider boundary should normalize all failures.
                    last_error = exc
                    if attempt < self.settings.provider_retry_count:
                        await asyncio.sleep(self.settings.provider_retry_delay_seconds)
            raise ProviderFailure(
                "provider_failed",
                f"Shazamio recognition failed: {last_error}",
                self.name,
                "audio_recognition",
                retryable=True,
            )
        finally:
            temp_path.unlink(missing_ok=True)


def provider_trace_from_failure(failure: ProviderFailure, fallback_used: bool) -> ProviderTrace:
    return ProviderTrace(
        provider=failure.provider,
        stage=failure.stage,
        fallback_used=fallback_used,
        fallback_reason=failure.message if fallback_used else None,
        retryable=failure.retryable,
        error_code=failure.code,
        message=failure.message,
    )


def _json_object(value: str) -> str:
    start = value.find("{")
    end = value.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return value
    return value[start : end + 1]


def _gemini_text(payload: dict[str, object]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return "{}"
    first = candidates[0]
    if not isinstance(first, dict):
        return "{}"
    content = first.get("content")
    if not isinstance(content, dict):
        return "{}"
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return "{}"
    first_part = parts[0]
    if not isinstance(first_part, dict):
        return "{}"
    text = first_part.get("text")
    return text if isinstance(text, str) else "{}"
