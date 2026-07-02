from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from seekphony_backend.api import register_routes
from seekphony_backend.core.config import Settings, get_settings
from seekphony_backend.core.errors import AppError, app_error_handler, validation_error_handler
from seekphony_backend.db import Database
from seekphony_backend.services.analytics import AnalyticsService
from seekphony_backend.services.catalog import CatalogService
from seekphony_backend.services.matching import MatchService
from seekphony_backend.services.metadata import MetadataService
from seekphony_backend.services.search import SearchService


@dataclass(slots=True)
class AppServices:
    settings: Settings
    db: Database
    catalog: CatalogService
    matcher: MatchService
    metadata: MetadataService
    search: SearchService
    analytics: AnalyticsService


def create_services(settings: Settings) -> AppServices:
    db = Database(settings)
    db.initialize()
    catalog = CatalogService(db)
    matcher = MatchService()
    metadata = MetadataService()
    search = SearchService(
        settings=settings,
        catalog=catalog,
        matcher=matcher,
        metadata=metadata,
    )
    analytics = AnalyticsService(db, catalog)
    return AppServices(
        settings=settings,
        db=db,
        catalog=catalog,
        matcher=matcher,
        metadata=metadata,
        search=search,
        analytics=analytics,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    services = create_services(resolved)
    app = FastAPI(
        title=resolved.app_name,
        version="0.1.0",
        description="Seekphony backend API for music search, catalog, recognition, and analytics.",
    )
    app.state.services = services
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_routes(app, services)
    return app


app = create_app()
