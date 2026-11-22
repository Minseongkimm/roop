"""Parse and build query strings. '+' is a space. Duplicate keys: last wins."""

from __future__ import annotations

from urllib.parse import quote, unquote_plus


def parse_query(text: str) -> dict[str, str]:
    raw: str = text[1:] if text.startswith("?") else text
    if raw == "":
        return {}
    parsed: dict[str, str] = {}
    for part in raw.split("&"):
        if part == "":
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        else:
            key, value = part, ""
        decoded_key: str = unquote_plus(key)
        if decoded_key == "":
            raise ValueError("empty query key")
        parsed[decoded_key] = unquote_plus(value)
    return parsed


def build_query(data: dict[str, str]) -> str:
    if not data:
        return ""
    parts: list[str] = []
    for key in sorted(data):
        encoded_key: str = quote(str(key), safe="")
        encoded_value: str = quote(str(data[key]), safe="")
        parts.append(f"{encoded_key}={encoded_value}")
    return "&".join(parts)
