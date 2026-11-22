"""Save and load a JSON object config file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_config(path: str, data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise TypeError("config data must be a dict")
    target: Path = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data), encoding="utf-8")


def load_config(path: str) -> Any:
    target: Path = Path(path)
    try:
        text: str = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        raise ValueError("invalid JSON") from err
