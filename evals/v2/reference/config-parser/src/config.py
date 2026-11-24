"""Process settings loaded from a simple key = value file."""

from __future__ import annotations

from pathlib import Path

DEFAULTS: dict[str, object] = {
    "low_stock_threshold": 5,
    "currency": "USD",
    "page_size": 20,
}

_KNOWN: frozenset[str] = frozenset(DEFAULTS)


def load_config(path: str) -> dict[str, object]:
    file_path: Path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(path)
    result: dict[str, object] = dict(DEFAULTS)
    seen: set[str] = set()
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line: str = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("invalid line")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in _KNOWN:
            raise ValueError("unknown key")
        if key in seen:
            raise ValueError("duplicate key")
        seen.add(key)
        result[key] = _parse_value(key, value)
    return result


def _parse_value(key: str, value: str) -> object:
    if key == "currency":
        if not value:
            raise ValueError("invalid currency")
        return value
    if key == "low_stock_threshold":
        number: int = _parse_int(value)
        if number < 0:
            raise ValueError("invalid low_stock_threshold")
        return number
    if key == "page_size":
        size: int = _parse_int(value)
        if size < 1:
            raise ValueError("invalid page_size")
        return size
    raise ValueError("unknown key")


def _parse_int(value: str) -> int:
    if value.startswith("-"):
        body: str = value[1:]
        if not body.isdigit():
            raise ValueError("invalid integer")
        return -int(body)
    if not value.isdigit():
        raise ValueError("invalid integer")
    return int(value)
