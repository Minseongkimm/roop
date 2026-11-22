"""Ollama HTTP client targeting localhost:11434."""

from __future__ import annotations

from typing import Sequence

import httpx

from roop.adapters.model import ChatMessage, ModelResponse

DEFAULT_OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_MODEL: str = "qwen2.5-coder:7b"


class OllamaClient:
    """Minimal Ollama chat/list/health client."""

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._timeout_seconds: float = timeout_seconds
        self._default_model: str = default_model

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response: httpx.Response = client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response: httpx.Response = client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                payload: dict[str, object] = response.json()
                models: object = payload.get("models", [])
                if not isinstance(models, list):
                    return []
                names: list[str] = []
                for item in models:
                    if isinstance(item, dict) and isinstance(item.get("name"), str):
                        names.append(item["name"])
                return names
        except httpx.HTTPError:
            return []

    def chat(self, messages: Sequence[ChatMessage], *, model: str | None = None) -> ModelResponse:
        selected_model: str = model or self._default_model
        body: dict[str, object] = {
            "model": selected_model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "stream": False,
        }
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response: httpx.Response = client.post(f"{self._base_url}/api/chat", json=body)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = response.text.strip()[:1500]
                message = f"{exc} | Ollama response: {detail}"
                raise httpx.HTTPStatusError(
                    message,
                    request=response.request,
                    response=response,
                ) from exc
            payload: dict[str, object] = response.json()
        message_obj: object = payload.get("message", {})
        content: str = ""
        if isinstance(message_obj, dict) and isinstance(message_obj.get("content"), str):
            content = message_obj["content"]
        done: bool = bool(payload.get("done", True))
        return ModelResponse(content=content, model=selected_model, done=done)
