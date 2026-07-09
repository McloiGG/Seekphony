from __future__ import annotations

import hmac
import urllib.parse
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import FastAPI, File, Form, Header, Query, UploadFile
from fastapi.responses import Response

from seekphony_backend.core.errors import AppError
from seekphony_backend.core.security import sha256_text
from seekphony_backend.schemas import (
    DeleteResponse,
    EvaluationListResponse,
    EvaluationResponse,
    HealthResponse,
    ReferenceImportRequest,
)

if TYPE_CHECKING:
    from seekphony_backend.application import AppServices


DEVICE_ID_HEADER = "X-Seekphony-Device-ID"
ADMIN_TOKEN_HEADER = "X-Seekphony-Admin-Token"


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
        device_id: str | None = Header(default=None, alias=DEVICE_ID_HEADER),
    ) -> EvaluationResponse:
        device_id_hash = _device_id_hash(device_id)
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
            device_id_hash=device_id_hash,
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

    @app.post(f"{api_prefix}/reference-audio/import")
    async def import_reference_audio(request: ReferenceImportRequest) -> Response:
        imported = await services.reference_imports.import_url(request.url)
        return Response(
            content=imported.content,
            media_type=imported.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{_header_quote(imported.filename)}"',
                "X-Seekphony-Filename": _header_quote(imported.filename),
                "X-Seekphony-Source-Type": imported.source_type,
                "X-Seekphony-Title": _header_quote(imported.title),
                "X-Seekphony-Byte-Size": str(imported.byte_size),
            },
        )

    @app.get(f"{api_prefix}/evaluations", response_model=EvaluationListResponse)
    async def list_evaluations(
        limit: int = Query(default=20, ge=1, le=100),
        device_id: str | None = Header(default=None, alias=DEVICE_ID_HEADER),
    ) -> EvaluationListResponse:
        return services.evaluations.list_evaluations(_device_id_hash(device_id), limit)

    @app.delete(f"{api_prefix}/evaluations", response_model=DeleteResponse)
    async def clear_evaluations(
        device_id: str | None = Header(default=None, alias=DEVICE_ID_HEADER),
    ) -> DeleteResponse:
        return services.evaluations.clear_evaluations(_device_id_hash(device_id))

    @app.delete(f"{api_prefix}/admin/evaluations", response_model=DeleteResponse)
    async def clear_all_evaluations(
        admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
    ) -> DeleteResponse:
        _require_admin_token(admin_token, services)
        return services.evaluations.clear_all_evaluations()

    @app.get(f"{api_prefix}/evaluations/{{evaluation_id}}", response_model=EvaluationResponse)
    async def get_evaluation(
        evaluation_id: int,
        device_id: str | None = Header(default=None, alias=DEVICE_ID_HEADER),
    ) -> EvaluationResponse:
        return services.evaluations.get_evaluation(evaluation_id, _device_id_hash(device_id))

    @app.delete(f"{api_prefix}/evaluations/{{evaluation_id}}", response_model=DeleteResponse)
    async def delete_evaluation(
        evaluation_id: int,
        device_id: str | None = Header(default=None, alias=DEVICE_ID_HEADER),
    ) -> DeleteResponse:
        return services.evaluations.delete_evaluation(evaluation_id, _device_id_hash(device_id))


def _device_id_hash(device_id: str | None) -> str:
    if not device_id or not device_id.strip():
        raise AppError(
            422,
            "validation_error",
            f"{DEVICE_ID_HEADER} is required for evaluation history.",
        )
    try:
        normalized = str(UUID(device_id.strip()))
    except ValueError as exc:
        raise AppError(
            422,
            "validation_error",
            f"{DEVICE_ID_HEADER} must be a valid UUID.",
        ) from exc
    return sha256_text(normalized)


def _require_admin_token(admin_token: str | None, services: AppServices) -> None:
    expected = services.settings.admin_token
    if not expected:
        raise AppError(
            403,
            "admin_disabled",
            "Admin evaluation cleanup is not configured.",
        )
    if not admin_token or not hmac.compare_digest(admin_token, expected):
        raise AppError(
            403,
            "forbidden",
            "Admin cleanup token is missing or invalid.",
        )


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


def _header_quote(value: str) -> str:
    return urllib.parse.quote(value, safe="._- ")
