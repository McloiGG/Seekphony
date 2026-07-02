from __future__ import annotations

from difflib import SequenceMatcher

from seekphony_backend.core.normalization import normalize_text
from seekphony_backend.schemas import Candidate, SongOut

FOUND_THRESHOLD = 90.0
CANDIDATE_THRESHOLD = 65.0


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return round(SequenceMatcher(None, left, right).ratio() * 100, 2)


class MatchService:
    def rank(
        self,
        songs: list[SongOut],
        *,
        query: str,
        title: str | None = None,
        artist: str | None = None,
        limit: int = 5,
    ) -> list[Candidate]:
        query_norm = normalize_text(query)
        title_norm = normalize_text(title)
        artist_norm = normalize_text(artist)
        candidates: list[Candidate] = []

        for song in songs:
            song_title = normalize_text(song.title)
            song_artist = normalize_text(song.artist)
            combined = normalize_text(f"{song.title} {song.artist}")
            scores = [
                similarity(query_norm, song_title),
                similarity(query_norm, combined),
            ]
            if title_norm:
                scores.append(similarity(title_norm, song_title))
            if artist_norm:
                scores.append(similarity(artist_norm, song_artist))
            if title_norm and artist_norm:
                scores.append(
                    (similarity(title_norm, song_title) * 0.7)
                    + (similarity(artist_norm, song_artist) * 0.3)
                )
            score = round(max(scores), 2)
            if score >= CANDIDATE_THRESHOLD:
                candidates.append(
                    Candidate(
                        song=song,
                        confidence=score,
                        reason=_reason(score),
                    )
                )

        candidates.sort(key=lambda item: item.confidence, reverse=True)
        return candidates[:limit]

    def classify(self, candidates: list[Candidate]) -> str:
        if candidates and candidates[0].confidence >= FOUND_THRESHOLD:
            return "found"
        if candidates:
            return "candidates"
        return "not_found"


def _reason(score: float) -> str:
    if score >= FOUND_THRESHOLD:
        return "High-confidence normalized metadata match."
    return "Potential match based on normalized fuzzy scoring."
