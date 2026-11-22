"""Exponential backoff delays in milliseconds."""

from __future__ import annotations


def backoff_ms(attempt: int, base_ms: int = 100) -> int:
    if attempt < 1 or base_ms < 0:
        raise ValueError("attempt must be >= 1 and base_ms must be >= 0")
    return base_ms * (2 ** (attempt - 1))
