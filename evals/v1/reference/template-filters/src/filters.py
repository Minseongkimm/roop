"""String filters used by the template renderer."""

from __future__ import annotations


def apply_filter(value: str, name: str, arg: str = "") -> str:
    if name == "upper":
        return value.upper()
    if name == "lower":
        return value.lower()
    if name == "default":
        if value == "":
            return arg
        return value
    raise ValueError(f"unknown filter: {name}")
