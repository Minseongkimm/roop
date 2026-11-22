"""Merge nested defaults. Data wins. Lists are replaced, not joined."""

from __future__ import annotations

from typing import Any


def apply_defaults(data: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(defaults, dict):
        raise TypeError("data and defaults must be dicts")
    return _merge(data, defaults)


def _merge(data: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in set(defaults) | set(data):
        if (
            key in data
            and key in defaults
            and isinstance(data[key], dict)
            and isinstance(defaults[key], dict)
        ):
            merged[key] = _merge(data[key], defaults[key])
        elif key in data:
            merged[key] = _copy(data[key])
        else:
            merged[key] = _copy(defaults[key])
    return merged


def _copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy(item) for item in value]
    return value
