"""Global HTTP exception handlers (structured JSON)."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from ..infra.tracer import trace
from ..schemas import ErrorCode, ErrorDetail, ErrorResponse


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        rid = _request_id(request)
        body = ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation failed.",
                request_id=rid,
                details=jsonable_encoder(exc.errors()),
            )
        )
        return JSONResponse(
            status_code=422,
            content=body.model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        rid = _request_id(request)
        detail = exc.detail
        if isinstance(detail, str):
            message = detail
        else:
            message = str(detail)
        code = ErrorCode.BAD_REQUEST
        if exc.status_code == 404:
            code = ErrorCode.NOT_FOUND
        elif exc.status_code >= 500:
            code = ErrorCode.INTERNAL_ERROR
        body = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
                request_id=rid,
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        rid = _request_id(request)
        trace(
            "unhandled_exception",
            {"type": exc.__class__.__name__, "error": str(exc)[:2000]},
            request_id=rid,
            component="http",
        )
        body = ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred.",
                request_id=rid,
                details=[{"type": exc.__class__.__name__}],
            )
        )
        return JSONResponse(
            status_code=500,
            content=body.model_dump(mode="json"),
        )
