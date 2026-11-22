"""Model Adapter interface — backends swap behind this contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Single chat turn for adapter backends."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Normalized model output."""

    content: str
    model: str
    done: bool = True


@runtime_checkable
class ModelAdapter(Protocol):
    """Replaceable inference backend (Ollama / MLX / llama.cpp)."""

    def chat(self, messages: Sequence[ChatMessage], *, model: str | None = None) -> ModelResponse:
        """Run a chat completion and return normalized text."""

    def is_available(self) -> bool:
        """Return True when the backend responds on its health endpoint."""

    def list_models(self) -> list[str]:
        """Return installed model tags, or empty when unavailable."""
