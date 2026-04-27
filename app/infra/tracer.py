"""
Structured trace lines for the agent and HTTP layer.

Each trace is one JSON object written to the file configured by LOG_FILE.
"""

from __future__ import annotations

from typing import Any

from .structured_log import log_record


def trace(
    kind: str,
    data: Any = None,
    *,
    request_id: str | None = None,
    component: str = "agent",
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Log a flow event. `data` may be a string or a small dict; long strings are truncated.
    """
    safe = _truncate_data(data)
    log_record(
        component=component,
        kind=kind,
        data=safe,
        request_id=request_id,
        extra=extra,
    )


def _truncate_data(data: Any, max_str: int = 4000) -> Any:
    if isinstance(data, str) and len(data) > max_str:
        return data[:max_str] + "…(truncated)"
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > max_str:
                out[k] = v[:max_str] + "…(truncated)"
            else:
                out[k] = v
        return out
    return data
