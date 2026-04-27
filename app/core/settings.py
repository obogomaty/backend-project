"""
Central settings from environment (.env + process env).

Typed, immutable snapshot — no extra packages beyond python-dotenv.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, *, min_v: int, max_v: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        n = int(raw.strip())
    except ValueError:
        return default
    return max(min_v, min(max_v, n))


def _env_float(name: str, default: float, *, min_v: float, max_v: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        x = float(raw.strip())
    except ValueError:
        return default
    return max(min_v, min(max_v, x))


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    cors_origins: str
    log_file: str
    log_level: str
    log_include_pid: bool
    max_input_chars: int
    max_llm_output_chars: int
    groq_model: str
    groq_temperature: float
    groq_top_p: float
    groq_max_completion_tokens: int
    groq_frequency_penalty: float
    groq_presence_penalty: float

    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        parts = [o.strip() for o in raw.split(",") if o.strip()]
        return parts if parts else ["*"]


def _load_settings() -> Settings:
    load_dotenv()
    return Settings(
        groq_api_key=(os.getenv("GROQ_API_KEY") or "").strip() or None,
        cors_origins=os.getenv("CORS_ORIGINS", "*").strip() or "*",
        log_file=os.getenv("LOG_FILE", "/tmp/app.log").strip() or "logs/app.log",
        log_level=(os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"),
        log_include_pid=_env_bool("LOG_INCLUDE_PID", False),
        max_input_chars=_env_int("MAX_INPUT_CHARS", 1000, min_v=20, max_v=200_000),
        max_llm_output_chars=_env_int(
            "MAX_LLM_OUTPUT_CHARS", 48_000, min_v=1024, max_v=500_000
        ),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
        or "llama-3.1-8b-instant",
        groq_temperature=_env_float("GROQ_TEMPERATURE", 0.7, min_v=0.0, max_v=2.0),
        groq_top_p=_env_float("GROQ_TOP_P", 1.0, min_v=0.0, max_v=1.0),
        groq_max_completion_tokens=_env_int(
            "GROQ_MAX_COMPLETION_TOKENS", 4096, min_v=256, max_v=131_072
        ),
        groq_frequency_penalty=_env_float(
            "GROQ_FREQUENCY_PENALTY", 0.0, min_v=-2.0, max_v=2.0
        ),
        groq_presence_penalty=_env_float(
            "GROQ_PRESENCE_PENALTY", 0.0, min_v=-2.0, max_v=2.0
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return _load_settings()


def clear_settings_cache() -> None:
    """For tests that mutate environment."""
    get_settings.cache_clear()
