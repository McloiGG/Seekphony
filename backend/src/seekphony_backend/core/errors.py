from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@dataclass(slots=True)
class AppError(Exception):
    status_code: int
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    provider: str | None = None
    stage: str | None = None
    fallback_used: bool = False

    def payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "fallback_used": self.fallback_used,
        }
        if self.provider:
            payload["provider"] = self.provider
        if self.stage:
            payload["stage"] = self.stage
        return payload


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.payload())


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_error",
            "message": "Request validation failed.",
            "details": {"errors": exc.errors()},
            "retryable": False,
            "fallback_used": False,
        },
    )
