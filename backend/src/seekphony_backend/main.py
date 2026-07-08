from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from seekphony_backend.api import register_routes
from seekphony_backend.core.config import Settings, get_settings
from seekphony_backend.core.errors import AppError, app_error_handler, validation_error_handler
from seekphony_backend.db import Database
from seekphony_backend.services.audio import AudioEvaluator
from seekphony_backend.services.evaluations import EvaluationService
from seekphony_backend.services.explanations import GeminiExplanationService


@dataclass(slots=True)
class AppServices:
    settings: Settings
    db: Database
    audio: AudioEvaluator
    explanations: GeminiExplanationService
    evaluations: EvaluationService


def create_services(settings: Settings) -> AppServices:
    db = Database(settings)
    db.initialize()
    audio = AudioEvaluator(settings.decode_timeout_seconds)
    explanations = GeminiExplanationService(settings)
    evaluations = EvaluationService(db=db, audio=audio, explanations=explanations)
    return AppServices(
        settings=settings,
        db=db,
        audio=audio,
        explanations=explanations,
        evaluations=evaluations,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    services = create_services(resolved)
    app = FastAPI(
        title=resolved.app_name,
        version="0.2.0",
        description="Seekphony backend API for explainable reference-match singing evaluation.",
    )
    app.state.services = services
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_routes(app, services)
    return app


app = create_app()
