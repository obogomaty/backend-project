"""
Post-generation checks. Full semantic "factuality" for free-form LLM text is not
solvable without external judges; we apply transparent, logged heuristics and
strong verification where the answer is deterministic (SymPy tool path).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from ..core.settings import Settings
from ..tools.math_tool import looks_like_structured_math, safe_math

Channel = Literal["sympy", "llm", "blocked", "config_error", "none"]

# Obvious secret / key leakage patterns in model output (log + soft flag).
_SECRETISH = re.compile(
    r"(gsk_[a-zA-Z0-9]{20,}|"
    r"sk-[a-zA-Z0-9]{20,}|"
    r"api[_-]?key\s*[:=]\s*[\w\-]{8,}|"
    r"Bearer\s+[A-Za-z0-9\-_]{20,})",
    re.IGNORECASE,
)


def _normalize_ws(s: str) -> str:
    return " ".join(s.split())


@dataclass
class AgentRunContext:
    user_message: str
    channel: Channel
    assistant_text: str
    request_id: str | None = None


@dataclass
class EvaluationReport:
    """Outcome of automated checks (informational + logged; does not replace human review)."""

    ok: bool
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_log_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checks": self.checks,
            "warnings": self.warnings,
        }


def evaluate_response(ctx: AgentRunContext, settings: Settings) -> EvaluationReport:
    checks: list[dict] = []
    warnings: list[str] = []
    ok = True

    text = ctx.assistant_text or ""

    # --- Size ---
    lim = settings.max_llm_output_chars
    size_ok = len(text) <= lim
    checks.append({"name": "output_length", "passed": size_ok, "len": len(text), "limit": lim})
    if not size_ok:
        ok = False
        warnings.append("assistant_output_exceeds_configured_max_length")

    # --- Secret leakage ---
    leak = _SECRETISH.search(text)
    leak_ok = leak is None
    checks.append({"name": "secret_leak_heuristic", "passed": leak_ok})
    if not leak_ok:
        ok = False
        warnings.append("possible_secret_pattern_in_output")

    if ctx.channel == "sympy":
        replay = safe_math(ctx.user_message)
        replay_err = str(replay).startswith("Error")
        replay_ok = not replay_err
        checks.append({"name": "sympy_replayable", "passed": replay_ok})
        if replay_ok:
            same = _normalize_ws(str(replay)) == _normalize_ws(text)
            checks.append({"name": "sympy_output_matches_replay", "passed": same})
            if not same:
                ok = False
                warnings.append("sympy_output_mismatch_vs_replay")
        else:
            ok = False
            warnings.append("sympy_replay_failed")

    elif ctx.channel == "llm":
        # Soft signals only — never treated as hard proof of correctness.
        math_like = looks_like_structured_math(ctx.user_message)
        has_final = bool(re.search(r"final\s+answer\s*:", text, re.IGNORECASE))
        checks.append(
            {
                "name": "math_final_answer_present",
                "passed": (not math_like) or has_final or len(text) < 400,
                "note": "heuristic_only",
                "user_looked_math_like": math_like,
            }
        )
        if math_like and not has_final and len(text) >= 400:
            warnings.append("long_math_reply_without_final_answer_line")

    else:
        # blocked | config_error | none — only generic checks above apply.
        checks.append(
            {"name": "channel", "passed": True, "value": ctx.channel},
        )

    return EvaluationReport(ok=ok, checks=checks, warnings=warnings)
