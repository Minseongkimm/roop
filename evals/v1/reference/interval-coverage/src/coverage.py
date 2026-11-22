"""Inclusive length of merged intervals, without double-counting overlaps."""

from __future__ import annotations

from src.intervals import merge_intervals


def covered_length(intervals: list[list[int]]) -> int:
    total: int = 0
    for start, end in merge_intervals(intervals):
        total += end - start + 1
    return total
