from __future__ import annotations

import re
from typing import TypedDict


class SafetyResult(TypedDict):
    passed: bool
    reasons: list[str]


_SAFETY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE), "Prompt injection pattern."),
    (re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b"), "Potential API key exposure."),
    (re.compile(r"\b(password|secret|token)\s*[:=]\s*\S+", re.IGNORECASE), "Potential secret disclosure."),
)


def _find_violations(text: str) -> list[str]:
    reasons: list[str] = []
    for pattern, reason in _SAFETY_PATTERNS:
        if pattern.search(text):
            reasons.append(reason)
    return reasons


def run_safety_gates(text: str) -> SafetyResult:
    reasons = _find_violations(text)
    return {"passed": not reasons, "reasons": reasons}
