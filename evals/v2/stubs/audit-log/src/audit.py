from __future__ import annotations

from typing import Any


class AuditLog:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, action: str, **fields: object) -> dict[str, Any]:
        del action, fields
        return {"id": 0, "action": "ignored"}

    def events(self) -> list[dict[str, Any]]:
        return []
