from __future__ import annotations

from typing import Protocol


class ModelAdapter(Protocol):
    def chat(self, messages: list[dict[str, str]]) -> str:
        """Return assistant text for a chat-completions style message list."""
