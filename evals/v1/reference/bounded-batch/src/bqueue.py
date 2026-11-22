"""A FIFO queue that refuses to grow past maxsize."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class BoundedQueue:
    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        self._maxsize: int = maxsize
        self._items: list[T] = []

    def push(self, item: T) -> None:
        if self.is_full():
            raise OverflowError("queue is full")
        self._items.append(item)

    def push_many(self, items: list[T]) -> None:
        incoming: list[T] = list(items)
        if len(self._items) + len(incoming) > self._maxsize:
            raise OverflowError("items do not fit")
        self._items.extend(incoming)

    def pop(self) -> T:
        if self.is_empty():
            raise IndexError("pop from empty queue")
        return self._items.pop(0)

    def peek(self) -> T:
        if self.is_empty():
            raise IndexError("peek from empty queue")
        return self._items[0]

    def size(self) -> int:
        return len(self._items)

    def is_full(self) -> bool:
        return len(self._items) >= self._maxsize

    def is_empty(self) -> bool:
        return not self._items
