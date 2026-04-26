import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ...core.settings import Settings, get_settings
from ...infra.tracer import trace
from ...schemas import (
    ChatRequest,
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    sse_delta_dict,
    sse_done_dict,
    sse_error_dict,
)
from ...services.agent_service import run_agent_stream

router = APIRouter(tags=["chat"])


@router.post(
    "/chat-stream",
    response_model=None,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Invalid JSON body or failed request validation.",
        },
    },
    summary="Stream chat completion (SSE)",
    description=(
        "Returns `text/event-stream` with events: `delta` (assistant text), "
        "`error` (`data` is JSON matching ErrorResponse), then `done`."
    ),
)
async def chat_stream(
    req: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> EventSourceResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    trace(
        "http_request",
        {"path": "/chat-stream", "message_len": len(req.message)},
        request_id=request_id,
        component="http",
    )

    async def event_generator() -> AsyncIterator[dict]:
        try:
            trace("sse_stream_open", {}, request_id=request_id, component="http")
            for piece in run_agent_stream(
                req.message,
                request_id=request_id,
                settings=settings,
            ):
                if piece:
                    yield sse_delta_dict(piece)
            trace(
                "sse_stream_close",
                {"ok": True},
                request_id=request_id,
                component="http",
            )
        except Exception as e:
            trace(
                "sse_stream_close",
                {"ok": False, "error": str(e)},
                request_id=request_id,
                component="http",
            )
            detail = ErrorDetail(
                code=ErrorCode.STREAM_ERROR,
                message=str(e)[:2000],
                request_id=request_id,
            )
            yield sse_error_dict(detail)
        yield sse_done_dict()

    return EventSourceResponse(event_generator())
