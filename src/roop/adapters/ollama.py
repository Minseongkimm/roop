"""Ollama HTTP client targeting localhost:11434."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Sequence

import httpx

from roop.adapters.model import ChatMessage, ModelResponse

DEFAULT_OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_MODEL: str = "qwen2.5-coder:7b"
DEFAULT_NUM_CTX: int = 8192
TRANSIENT_ATTEMPTS: int = 4
TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_BACKOFF_SECONDS: float = 0.5


class TransientOllamaError(RuntimeError):
    """Ollama kept returning a transient error after backoff retries."""


class OllamaClient:
    """Minimal Ollama chat/list/health client."""

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        default_model: str = DEFAULT_MODEL,
        *,
        num_ctx: int = DEFAULT_NUM_CTX,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._timeout_seconds: float = timeout_seconds
        self._default_model: str = default_model
        self._num_ctx: int = num_ctx
        self._sleeper: Callable[[float], None] = sleeper or time.sleep

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
            "format": "json",
            "options": {
                "temperature": 0.1,
                "repeat_penalty": 1.15,
                "repeat_last_n": 128,
                "num_predict": 8192,
                "num_ctx": self._num_ctx,
            },
            "stream": False,
        }
        payload: dict[str, object] = self._post_chat(body)
        message_obj: object = payload.get("message", {})
        content: str = ""
        if isinstance(message_obj, dict) and isinstance(message_obj.get("content"), str):
            content = message_obj["content"]
        done: bool = bool(payload.get("done", True))
        return ModelResponse(content=content, model=selected_model, done=done)

    def _post_chat(self, body: dict[str, object]) -> dict[str, object]:
        """POST /api/chat. Transient failures sleep and retry outside the task budget."""
        delay: float = _BACKOFF_SECONDS
        with httpx.Client(timeout=self._timeout_seconds) as client:
            for attempt in range(TRANSIENT_ATTEMPTS):
                try:
                    response: httpx.Response = client.post(
                        f"{self._base_url}/api/chat",
                        json=body,
                    )
                except httpx.TransportError as exc:
                    if attempt + 1 >= TRANSIENT_ATTEMPTS:
                        raise TransientOllamaError(str(exc)) from exc
                    self._sleeper(delay)
                    delay *= 2
                    continue
                status_code: object = getattr(response, "status_code", 200)
                if isinstance(status_code, int) and status_code in TRANSIENT_STATUS_CODES:
                    if attempt + 1 >= TRANSIENT_ATTEMPTS:
                        detail: str = response.text.strip()[:300]
                        raise TransientOllamaError(f"HTTP {status_code}: {detail}")
                    self._sleeper(delay)
                    delay *= 2
                    continue
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
                payload: object = response.json()
                if isinstance(payload, dict):
                    return payload
                return {}
        raise TransientOllamaError("Ollama chat failed without a response")
