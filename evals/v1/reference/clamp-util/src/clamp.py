"""Clamp a value into an inclusive range."""

from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    if low > high:
        raise ValueError("low must be less than or equal to high")
    if value < low:
        return low
    if value > high:
        return high
    return value
