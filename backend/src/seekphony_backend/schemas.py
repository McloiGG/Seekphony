from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Scores(BaseModel):
    overall: float = Field(ge=0, le=100)
    pitch: float = Field(ge=0, le=100)
    rhythm: float = Field(ge=0, le=100)
    stability: float = Field(ge=0, le=100)
    coverage: float = Field(ge=0, le=100)
    audio_quality: float = Field(ge=0, le=100)


class Metrics(BaseModel):
    key_shift_semitones: int | None = None
    pitch_error_cents: float | None = None
    timing_offset_ms: float | None = None
    voiced_coverage: float = Field(ge=0, le=1)
    reference_voiced_ratio: float = Field(ge=0, le=1)
    performance_voiced_ratio: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reference_duration_seconds: float = Field(gt=0)
    performance_duration_seconds: float = Field(gt=0)


class ProblemSegment(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    issue: Literal["missing_voice", "pitch", "timing", "low_confidence"]
    severity: Literal["low", "medium", "high"]
    detail: str


class ExplanationContent(BaseModel):
    summary: str = Field(min_length=1, max_length=800)
    strengths: list[str] = Field(default_factory=list, max_length=5)
    focus_areas: list[str] = Field(default_factory=list, max_length=5)
    practice_steps: list[str] = Field(default_factory=list, max_length=5)


class Explanation(BaseModel):
    status: Literal["available", "unavailable", "error"]
    provider: str = "gemini"
    error: str | None = None
    content: ExplanationContent | None = None


class EvaluationResponse(BaseModel):
    status: Literal["completed"]
    evaluation_id: int
    created_at: str
    reference_filename: str
    performance_filename: str
    clip_start_seconds: float
    clip_duration_seconds: float
    performance_start_seconds: float
    scores: Scores
    metrics: Metrics
    segments: list[ProblemSegment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: Explanation


class EvaluationListResponse(BaseModel):
    status: Literal["ok"]
    evaluations: list[EvaluationResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    api_prefix: str
    database: dict[str, Any]
    providers: dict[str, bool]
    limits: dict[str, float | int]
