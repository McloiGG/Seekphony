from __future__ import annotations

import hashlib
from typing import Any

from seekphony_backend.core.errors import AppError
from seekphony_backend.db import Database, utc_now_iso
from seekphony_backend.schemas import (
    DeleteResponse,
    EvaluationListResponse,
    EvaluationResponse,
    Explanation,
    Metrics,
    ProblemSegment,
    Scores,
)
from seekphony_backend.services.audio import AudioEvaluator
from seekphony_backend.services.explanations import GeminiExplanationService


class EvaluationService:
    def __init__(
        self,
        db: Database,
        audio: AudioEvaluator,
        explanations: GeminiExplanationService,
    ) -> None:
        self.db = db
        self.audio = audio
        self.explanations = explanations

    async def create_evaluation(
        self,
        *,
        reference_content: bytes,
        reference_filename: str,
        performance_content: bytes,
        performance_filename: str,
        clip_start_seconds: float,
        clip_duration_seconds: float,
        performance_start_seconds: float,
    ) -> EvaluationResponse:
        analysis = self.audio.evaluate(
            reference_content,
            reference_filename,
            performance_content,
            performance_filename,
            clip_start_seconds,
            clip_duration_seconds,
            performance_start_seconds,
        )
        scores = Scores.model_validate(analysis["scores"])
        metrics = Metrics.model_validate(analysis["metrics"])
        segments = [ProblemSegment.model_validate(segment) for segment in analysis["segments"]]
        warnings = [str(warning) for warning in analysis["warnings"]]
        explanation = await self.explanations.explain(
            scores=scores.model_dump(),
            metrics=metrics.model_dump(),
            segments=[segment.model_dump() for segment in segments],
            warnings=warnings,
        )
        created_at = utc_now_iso()
        row = {
            "created_at": created_at,
            "reference_filename": reference_filename,
            "performance_filename": performance_filename,
            "reference_sha256": _sha256(reference_content),
            "performance_sha256": _sha256(performance_content),
            "clip_start_seconds": clip_start_seconds,
            "clip_duration_seconds": clip_duration_seconds,
            "performance_start_seconds": performance_start_seconds,
            "overall_score": scores.overall,
            "pitch_score": scores.pitch,
            "rhythm_score": scores.rhythm,
            "stability_score": scores.stability,
            "coverage_score": scores.coverage,
            "audio_quality_score": scores.audio_quality,
            "key_shift_semitones": metrics.key_shift_semitones,
            "pitch_error_cents": metrics.pitch_error_cents,
            "timing_offset_ms": metrics.timing_offset_ms,
            "voiced_coverage": metrics.voiced_coverage,
            "confidence": metrics.confidence,
            "metrics_json": metrics.model_dump(),
            "segments_json": [segment.model_dump() for segment in segments],
            "warnings_json": warnings,
            "explanation_status": explanation.status,
            "explanation_error": explanation.error,
            "explanation_json": (
                explanation.content.model_dump() if explanation.content is not None else None
            ),
        }
        evaluation_id = self.db.create_evaluation(row)
        return EvaluationResponse(
            status="completed",
            evaluation_id=evaluation_id,
            created_at=created_at,
            reference_filename=reference_filename,
            performance_filename=performance_filename,
            clip_start_seconds=clip_start_seconds,
            clip_duration_seconds=clip_duration_seconds,
            performance_start_seconds=performance_start_seconds,
            scores=scores,
            metrics=metrics,
            segments=segments,
            warnings=warnings,
            explanation=explanation,
        )

    def list_evaluations(self, limit: int = 20) -> EvaluationListResponse:
        rows = self.db.list_evaluations(limit)
        return EvaluationListResponse(
            status="ok",
            evaluations=[_response_from_row(row) for row in rows],
        )

    def get_evaluation(self, evaluation_id: int) -> EvaluationResponse:
        row = self.db.get_evaluation(evaluation_id)
        if row is None:
            raise AppError(
                404,
                "not_found",
                "Evaluation was not found.",
                {"evaluation_id": evaluation_id},
            )
        return _response_from_row(row)

    def delete_evaluation(self, evaluation_id: int) -> DeleteResponse:
        if not self.db.delete_evaluation(evaluation_id):
            raise AppError(
                404,
                "not_found",
                "Evaluation was not found.",
                {"evaluation_id": evaluation_id},
            )
        return DeleteResponse(status="ok", deleted_count=1)

    def clear_evaluations(self) -> DeleteResponse:
        return DeleteResponse(status="ok", deleted_count=self.db.clear_evaluations())


def _response_from_row(row: dict[str, Any]) -> EvaluationResponse:
    explanation_content = row.get("explanation_json")
    explanation = Explanation(
        status=row["explanation_status"],
        error=row.get("explanation_error"),
        content=explanation_content,
    )
    return EvaluationResponse(
        status="completed",
        evaluation_id=int(row["id"]),
        created_at=row["created_at"],
        reference_filename=row["reference_filename"],
        performance_filename=row["performance_filename"],
        clip_start_seconds=float(row["clip_start_seconds"]),
        clip_duration_seconds=float(row["clip_duration_seconds"]),
        performance_start_seconds=float(row["performance_start_seconds"]),
        scores=Scores(
            overall=float(row["overall_score"]),
            pitch=float(row["pitch_score"]),
            rhythm=float(row["rhythm_score"]),
            stability=float(row["stability_score"]),
            coverage=float(row["coverage_score"]),
            audio_quality=float(row["audio_quality_score"]),
        ),
        metrics=Metrics.model_validate(row["metrics_json"]),
        segments=[ProblemSegment.model_validate(segment) for segment in row["segments_json"]],
        warnings=list(row["warnings_json"]),
        explanation=explanation,
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
