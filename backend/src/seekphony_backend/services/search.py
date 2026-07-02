from __future__ import annotations

from seekphony_backend.core.config import Settings
from seekphony_backend.schemas import ExtractedMetadata, ProviderTrace, SearchResponse
from seekphony_backend.services.catalog import CatalogService
from seekphony_backend.services.matching import MatchService
from seekphony_backend.services.metadata import MetadataService
from seekphony_backend.services.providers import (
    GeminiTextProvider,
    LocalTextProvider,
    ProviderFailure,
    ShazamioAudioProvider,
    provider_trace_from_failure,
)


class SearchService:
    def __init__(
        self,
        *,
        settings: Settings,
        catalog: CatalogService,
        matcher: MatchService,
        metadata: MetadataService,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.matcher = matcher
        self.metadata = metadata
        self.local_text = LocalTextProvider()
        self.gemini = GeminiTextProvider(settings)
        self.shazamio = ShazamioAudioProvider(settings)

    async def search_text(self, query: str) -> SearchResponse:
        provider = ProviderTrace(provider="gemini", stage="text_extraction")
        try:
            extracted = await self.gemini.extract(query)
        except ProviderFailure as failure:
            extracted = self.local_text.extract(query)
            provider = provider_trace_from_failure(failure, fallback_used=True)
            provider.provider = extracted.provider
            provider.stage = "text_extraction"
        else:
            provider = ProviderTrace(provider=extracted.provider, stage="text_extraction")

        return self._match_and_record(
            query_type="text",
            input_summary=query,
            extracted=extracted,
            provider=provider,
            fallback_used=provider.fallback_used or extracted.fallback_used,
        )

    async def search_audio(self, content: bytes, filename: str | None) -> SearchResponse:
        input_summary = filename or "uploaded-audio"
        try:
            extracted = await self.shazamio.recognize(content, filename)
            provider = ProviderTrace(provider=extracted.provider, stage="audio_recognition")
        except ProviderFailure as failure:
            extracted = self.metadata.extract_from_file(content, filename)
            provider = provider_trace_from_failure(failure, fallback_used=True)
            provider.provider = extracted.provider
            provider.stage = "audio_recognition"

        query = " ".join(part for part in [extracted.title, extracted.artist, filename] if part)
        return self._match_and_record(
            query_type="audio",
            input_summary=input_summary,
            extracted=extracted,
            provider=provider,
            fallback_used=provider.fallback_used or extracted.fallback_used,
            query=query or input_summary,
        )

    def _match_and_record(
        self,
        *,
        query_type: str,
        input_summary: str,
        extracted: ExtractedMetadata,
        provider: ProviderTrace,
        fallback_used: bool,
        query: str | None = None,
    ) -> SearchResponse:
        songs = self.catalog.list_songs()
        ranked = self.matcher.rank(
            songs,
            query=query or input_summary,
            title=extracted.title,
            artist=extracted.artist,
        )
        status = self.matcher.classify(ranked)
        song = ranked[0].song if status == "found" else None
        if song:
            self.catalog.set_last_recognized(song.id)

        self.catalog.record_recognition(
            query_type=query_type,
            provider=provider.provider,
            status=status,
            input_summary=input_summary,
            extracted_title=extracted.title,
            extracted_artist=extracted.artist,
            confidence=ranked[0].confidence if ranked else extracted.confidence,
            matched_song_id=song.id if song else None,
            fallback_used=fallback_used,
            fallback_reason=provider.fallback_reason or extracted.fallback_reason,
            error_code=provider.error_code,
            error_message=provider.message,
        )

        if status == "found":
            message = f'Match found: "{song.title}" by {song.artist}.'
        elif status == "candidates":
            message = "No exact match found; ranked candidates are available."
        else:
            message = "No song available in database, do you want to add the song?"

        return SearchResponse(
            status=status,  # type: ignore[arg-type]
            query_type=query_type,  # type: ignore[arg-type]
            provider=provider,
            extracted=extracted,
            song=song,
            candidates=ranked,
            message=message,
        )
