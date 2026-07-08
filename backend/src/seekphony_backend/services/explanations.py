from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

from pydantic import ValidationError

from seekphony_backend.core.config import Settings
from seekphony_backend.schemas import Explanation, ExplanationContent


class GeminiExplanationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def explain(
        self,
        *,
        scores: dict[str, Any],
        metrics: dict[str, Any],
        segments: list[dict[str, Any]],
        warnings: list[str],
    ) -> Explanation:
        if not self.settings.gemini_api_key:
            return Explanation(
                status="unavailable",
                error="Gemini API key is not configured.",
                content=None,
            )
        try:
            content = await asyncio.to_thread(
                self._request_explanation,
                scores,
                metrics,
                segments,
                warnings,
            )
        except Exception as exc:  # The user should see that AI failed while metrics remain usable.
            return Explanation(status="error", error=_safe_error(exc), content=None)
        return Explanation(status="available", content=content)

    def _request_explanation(
        self,
        scores: dict[str, Any],
        metrics: dict[str, Any],
        segments: list[dict[str, Any]],
        warnings: list[str],
    ) -> ExplanationContent:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent?key={self.settings.gemini_api_key}"
        )
        prompt = {
            "task": "Explain a reference-match singing evaluation for a learner.",
            "rules": [
                "Use only the supplied metrics and warnings.",
                "Do not claim to hear the audio.",
                "Mention key shift when present.",
                "Mention low confidence or noisy audio when warnings indicate it.",
                "Return concise coaching text.",
            ],
            "required_json_shape": {
                "summary": "string",
                "strengths": ["string"],
                "focus_areas": ["string"],
                "practice_steps": ["string"],
            },
            "scores": scores,
            "metrics": metrics,
            "segments": segments[:5],
            "warnings": warnings,
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Return only valid JSON matching the required_json_shape. "
                                f"Input: {json.dumps(prompt, separators=(',', ':'))}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310 - URL is the configured Gemini endpoint.
                request,
                timeout=self.settings.provider_timeout_seconds,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini returned HTTP {exc.code}: {body[:300]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

        text = _extract_gemini_text(response_payload)
        try:
            parsed = json.loads(text)
            return ExplanationContent.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise RuntimeError("Gemini returned an invalid explanation payload.") from exc


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list) or not parts:
        raise RuntimeError("Gemini returned no text parts.")
    text = parts[0].get("text") if isinstance(parts[0], dict) else None
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Gemini returned an empty explanation.")
    return text.strip()


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return "Gemini explanation failed."
    return message[:500]
