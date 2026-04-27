"""HTTP and stream error payloads (single envelope shape)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    """Stable machine-readable codes for clients and logs."""

    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    NOT_FOUND = "not_found"
    INTERNAL_ERROR = "internal_error"
    STREAM_ERROR = "stream_error"


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode = Field(description="Stable error category")
    message: str = Field(description="Human-readable summary")
    request_id: str | None = Field(
        default=None,
        description="Correlation id (matches X-Request-ID when present)",
    )
    details: list[Any] | None = Field(
        default=None,
        description="Extra context (e.g. Pydantic validation error list)",
    )


class ErrorResponse(BaseModel):
    """Standard JSON error body for non-SSE HTTP responses."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail = Field(description="Error payload")
