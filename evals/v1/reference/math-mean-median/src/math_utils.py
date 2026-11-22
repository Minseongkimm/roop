"""Mean and median. Does not mutate the input."""

from __future__ import annotations


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) / len(values)


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires at least one value")
    ordered: list[float] = sorted(values)
    middle: int = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2
