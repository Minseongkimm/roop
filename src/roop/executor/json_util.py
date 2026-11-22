"""Extract JSON objects from model text (Phase 4)."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned: str = text.strip()
    if not cleaned:
        raise ValueError("empty model output")
    candidates: list[str] = []
    fenced: list[str] = _FENCE_RE.findall(cleaned)
    candidates.extend(item.strip() for item in fenced if item.strip())
    candidates.append(cleaned)
    start: int = cleaned.find("{")
    end: int = cleaned.rfind("}")
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            payload: Any = json.loads(candidate)
        except json.JSONDecodeError as err:
            last_error = err
            continue
        if isinstance(payload, dict):
            return payload
        last_error = ValueError("JSON root is not an object")
    if last_error is not None:
        raise ValueError(f"failed to parse JSON object: {last_error}") from last_error
    raise ValueError("failed to parse JSON object")
