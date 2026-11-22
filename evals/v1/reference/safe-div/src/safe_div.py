"""Division that returns a default when the divisor is zero."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def safe_div(a: float, b: float, default: T | None = None) -> float | T | None:
    if b == 0:
        return default
    return a / b
