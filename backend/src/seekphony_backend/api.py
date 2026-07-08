from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, File, Form, Query, UploadFile

from seekphony_backend.core.errors import AppError
from seekphony_backend.schemas import EvaluationListResponse, EvaluationResponse, HealthResponse

if TYPE_CHECKING:
    from seekphony_backend.main import AppServices


def register_routes(app: FastAPI, services: AppServices) -> None:
    api_prefix = services.settings.api_prefix

    @app.get("/health", response_model=HealthResponse)
    @app.get(f"{api_prefix}/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=services.settings.app_name,
            api_prefix=api_prefix,
            database={
                "kind": services.settings.database_kind,
                "postgres_configured": services.settings.database_kind == "postgres",
            },
            providers={"gemini_configured": bool(services.settings.gemini_api_key)},
            limits={
                "max_upload_bytes": services.settings.max_upload_bytes,
                "min_clip_seconds": services.settings.min_clip_seconds,
                "max_clip_seconds": services.settings.max_clip_seconds,
            },
        )

    @app.get(f"{api_prefix}")
    async def api_root() -> dict[str, Any]:
        return {
            "status": "active",
            "message": f"Welcome to the {services.settings.app_name} evaluation API.",
            "documentation": "/docs",
        }

    @app.post(f"{api_prefix}/evaluations", response_model=EvaluationResponse)
    async def create_evaluation(
        reference: UploadFile = File(...),
        performance: UploadFile = File(...),
        clip_start_seconds: float = Form(0.0),
        clip_duration_seconds: float = Form(30.0),
        performance_start_seconds: float | None = Form(None),
    ) -> EvaluationResponse:
        _validate_clip_bounds(clip_start_seconds, clip_duration_seconds, services)
        reference_content = await reference.read()
        performance_content = await performance.read()
        _validate_upload(reference_content, reference.filename, services.settings.max_upload_bytes)
        _validate_upload(
            performance_content,
            performance.filename,
            services.settings.max_upload_bytes,
        )
        return await services.evaluations.create_evaluation(
            reference_content=reference_content,
            reference_filename=_filename(reference),
            performance_content=performance_content,
            performance_filename=_filename(performance),
            clip_start_seconds=clip_start_seconds,
            clip_duration_seconds=clip_duration_seconds,
            performance_start_seconds=(
                performance_start_seconds if performance_start_seconds is not None else 0.0
            ),
        )

    @app.get(f"{api_prefix}/evaluations", response_model=EvaluationListResponse)
    async def list_evaluations(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> EvaluationListResponse:
        return services.evaluations.list_evaluations(limit)

    @app.get(f"{api_prefix}/evaluations/{{evaluation_id}}", response_model=EvaluationResponse)
    async def get_evaluation(evaluation_id: int) -> EvaluationResponse:
        return services.evaluations.get_evaluation(evaluation_id)


def _validate_clip_bounds(
    clip_start_seconds: float,
    clip_duration_seconds: float,
    services: AppServices,
) -> None:
    if clip_start_seconds < 0:
        raise AppError(422, "validation_error", "Clip start must be zero or greater.")
    if not (
        services.settings.min_clip_seconds
        <= clip_duration_seconds
        <= services.settings.max_clip_seconds
    ):
        raise AppError(
            422,
            "validation_error",
            "Clip duration is outside the configured evaluation range.",
            {
                "min_clip_seconds": services.settings.min_clip_seconds,
                "max_clip_seconds": services.settings.max_clip_seconds,
            },
        )


def _validate_upload(content: bytes, filename: str | None, max_bytes: int) -> None:
    if not content:
        raise AppError(422, "validation_error", "Uploaded audio file is empty.")
    if len(content) > max_bytes:
        raise AppError(
            413,
            "file_too_large",
            "Payload length exceeds the configured maximum upload size.",
            {"filename": filename, "max_upload_bytes": max_bytes},
        )


def _filename(upload: UploadFile) -> str:
    return upload.filename or "uploaded-audio.wav"
