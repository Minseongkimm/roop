"""Flatten exactly one nesting level."""

from __future__ import annotations

from typing import Any


def flatten_once(seq: list[Any]) -> list[Any]:
    flattened: list[Any] = []
    for item in seq:
        if isinstance(item, list):
            flattened.extend(item)
            continue
        flattened.append(item)
    return flattened
