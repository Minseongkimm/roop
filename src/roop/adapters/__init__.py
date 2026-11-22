"""Model adapters for local and remote inference backends."""

from roop.adapters.model import ChatMessage, ModelAdapter, ModelResponse
from roop.adapters.ollama import OllamaClient

__all__ = [
    "ChatMessage",
    "ModelAdapter",
    "ModelResponse",
    "OllamaClient",
]
