"""Rough token budget helpers for context packets."""

from __future__ import annotations

DEFAULT_TOKEN_BUDGET: int = 8000
CHARS_PER_TOKEN: float = 4.0


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def truncate_to_tokens(text: str, *, max_tokens: int) -> str:
    if max_tokens <= 0 or not text:
        return ""
    max_chars: int = int(max_tokens * CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    clipped: str = text[: max(0, max_chars - 20)].rstrip()
    return f"{clipped}\n…(truncated)"
