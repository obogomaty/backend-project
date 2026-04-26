"""HTTP middleware."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns ``request.state.request_id`` and echoes ``X-Request-ID`` on the response.
    If the client sends a non-empty ``X-Request-ID`` header (trimmed, max 128 chars), it is reused.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        raw = (request.headers.get("x-request-id") or "").strip()
        if raw and len(raw) <= 128:
            rid = raw
        else:
            rid = str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
