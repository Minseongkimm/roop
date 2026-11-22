"""Drain a bounded queue up to a limit."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def drain(queue: object, limit: int) -> list[T]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    drained: list[T] = []
    is_empty = getattr(queue, "is_empty")
    pop = getattr(queue, "pop")
    while len(drained) < limit and not is_empty():
        drained.append(pop())
    return drained
