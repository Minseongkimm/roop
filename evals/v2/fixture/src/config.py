"""Process settings. load_config is a stub until the parser task is implemented."""

from __future__ import annotations

DEFAULTS: dict[str, object] = {
    "low_stock_threshold": 5,
    "currency": "USD",
    "page_size": 20,
}


def load_config(path: str) -> dict[str, object]:
    raise NotImplementedError("load_config is not implemented")
