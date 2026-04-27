"""
Server-Sent Event payloads for POST /chat-stream.

Groq / Starlette emit `event` + `data` lines; `data` is always a string. For `event: error`,
`data` is JSON matching :class:`ErrorResponse` so clients can reuse the same parser as HTTP errors.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .errors import ErrorDetail, ErrorResponse


class SSEDeltaEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: Literal["delta"] = "delta"
    data: str = Field(default="", description="Assistant text fragment")


class SSEDoneEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: Literal["done"] = "done"
    data: str = Field(default="", description="Empty sentinel; stream complete")


def sse_delta_dict(text: str) -> dict:
    """Shape expected by sse-starlette for a token chunk."""
    return SSEDeltaEvent(data=text).model_dump(mode="json")


def sse_done_dict() -> dict:
    return SSEDoneEvent().model_dump(mode="json")


def sse_error_dict(detail: ErrorDetail) -> dict:
    """JSON string in `data` matches :class:`ErrorResponse` for unified client parsing."""
    body = ErrorResponse(error=detail)
    return {
        "event": "error",
        "data": body.model_dump_json(),
    }
