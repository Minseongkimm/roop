"""In-memory audit log for inventory actions."""

from __future__ import annotations

from typing import Any


class AuditLog:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, action: str, **fields: object) -> dict[str, Any]:
        event: dict[str, Any] = {"id": len(self._events) + 1, "action": action}
        event.update(fields)
        self._events.append(event)
        return dict(event)

    def events(self) -> list[dict[str, Any]]:
        return [dict(event) for event in self._events]
