"""Trivial stub: always returns a copy of the defaults and ignores the file."""

from __future__ import annotations

DEFAULTS: dict[str, object] = {
    "low_stock_threshold": 5,
    "currency": "USD",
    "page_size": 20,
}


def load_config(path: str) -> dict[str, object]:
    del path
    return dict(DEFAULTS)
