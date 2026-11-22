"""Sort and merge inclusive intervals without mutating the input."""

from __future__ import annotations


def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    copied: list[list[int]] = [list(item) for item in intervals]
    for start, end in copied:
        if start > end:
            raise ValueError("start must be less than or equal to end")
    ordered: list[list[int]] = sorted(copied, key=lambda item: (item[0], item[1]))
    merged: list[list[int]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
            continue
        merged[-1][1] = max(merged[-1][1], end)
    return merged
