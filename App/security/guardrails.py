"""
User-message validation: size limits, code-injection strings, prompt-injection heuristics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..core.settings import Settings

# Substrings that suggest code execution or host abuse (case-insensitive scan).
_CODE_INJECTION_MARKERS: tuple[str, ...] = (
    "import ",
    "import\t",
    "__import__",
    "__builtins__",
    "__globals__",
    "__class__",
    "os.system",
    "subprocess",
    "eval(",
    "exec(",
    "compile(",
    "pickle.loads",
    "yaml.load",
)

# Heuristic patterns for role / instruction hijacking (case-insensitive).
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.DOTALL)
    for p in (
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)",
        r"disregard\s+(all\s+)?(previous|prior|above)",
        r"forget\s+(everything|all)\s+(you|above)",
        r"new\s+(system\s+)?instructions?\s*[:\-]",
        r"<\|system\|>",
        r"<\|im_start\|>\s*system",
        r"\[INST\]",
        r"###\s*system",
        r"you\s+are\s+now\s+(allowed|free|unrestricted)",
        r"developer\s+mode",
        r"jailbreak",
        r"\bDAN\b.*\bmode\b",
        r"reveal\s+(your|the)\s+(api|secret|key|password|token)",
        r"print\s+the\s+(api|secret|key|env)",
        r"override\s+(safety|guardrails?|policy)",
    )
)

# Suspicious density: many control / zero-width / RTL override chars.
_CONTROL_CHAR_RATIO_THRESHOLD = 0.08


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason_code: str | None = None
    detail: str | None = None


def _controlish_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(
        1
        for c in text
        if ord(c) < 32 and c not in "\n\r\t"
        or 0x200B <= ord(c) <= 0x200F  # zero-width space / marks
        or 0x202A <= ord(c) <= 0x202E  # bidi overrides
    )
    return bad / len(text)


def validate_user_message(text: str, settings: Settings) -> GuardrailResult:
    if text is None:
        return GuardrailResult(False, "empty", "Message is missing.")

    stripped = text.strip()
    if not stripped:
        return GuardrailResult(False, "empty", "Message is empty.")

    if len(text) > settings.max_input_chars:
        return GuardrailResult(
            False,
            "input_too_large",
            f"Message exceeds max length ({settings.max_input_chars} characters).",
        )

    lower = text.lower()
    for marker in _CODE_INJECTION_MARKERS:
        if marker in lower:
            return GuardrailResult(
                False,
                "code_injection",
                "Message contains disallowed code-execution patterns.",
            )

    for pat in _INJECTION_PATTERNS:
        if pat.search(text):
            return GuardrailResult(
                False,
                "prompt_injection",
                "Message matched a prompt-injection heuristic.",
            )

    ratio = _controlish_ratio(text)
    if ratio > _CONTROL_CHAR_RATIO_THRESHOLD:
        return GuardrailResult(
            False,
            "suspicious_encoding",
            "Message contains an unusual density of control or hidden characters.",
        )

    return GuardrailResult(True, None, None)
