"""Chat API request bodies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{"message": "What is the derivative of x**2 + 3?"}],
        },
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=200_000,
        description="User message. Further limits may apply server-side (see MAX_INPUT_CHARS).",
    )
