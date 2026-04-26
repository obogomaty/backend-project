"""
JSON-lines file logging for request/agent flow (one JSON object per line).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.settings import get_settings

_configured = False


def _level_value(name: str) -> int:
    return getattr(logging, name.upper(), logging.INFO)


def setup_logging() -> None:
    """Attach a single file handler to the app flow logger (idempotent)."""
    global _configured
    if _configured:
        return

    settings = get_settings()
    path = Path(settings.log_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = logging.getLogger("app.flow")
    logger.setLevel(_level_value(settings.log_level))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    _configured = True


def get_flow_logger() -> logging.Logger:
    setup_logging()
    return logging.getLogger("app.flow")


def log_record(
    *,
    component: str,
    kind: str,
    data: Any = None,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit one JSON line to the log file."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "kind": kind,
        "data": data,
    }
    if request_id:
        payload["request_id"] = request_id
    if extra:
        payload["extra"] = extra
    if settings.log_include_pid:
        import os

        payload["pid"] = os.getpid()
    get_flow_logger().info(json.dumps(payload, ensure_ascii=False, default=str))
