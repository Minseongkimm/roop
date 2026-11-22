"""Most-common items, ties broken by the item itself."""

from __future__ import annotations

from collections import Counter
from typing import TypeVar

T = TypeVar("T")


def top_n(items: list[T], n: int) -> list[tuple[T, int]]:
    if n < 1:
        raise ValueError("n must be at least 1")
    counts: Counter[T] = Counter(items)
    ranked: list[tuple[T, int]] = sorted(
        counts.items(),
        key=lambda pair: (-pair[1], str(pair[0])),
    )
    return ranked[:n]
