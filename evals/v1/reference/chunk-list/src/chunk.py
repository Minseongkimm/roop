"""Split a sequence into consecutive chunks of a fixed size."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def chunk_list(items: list[T], size: int) -> list[list[T]]:
    if size < 1:
        raise ValueError("size must be at least 1")
    return [list(items[index : index + size]) for index in range(0, len(items), size)]
