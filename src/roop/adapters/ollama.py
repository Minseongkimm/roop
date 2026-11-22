from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL: str = "http://127.0.0.1:11434"
DEFAULT_MODEL: str = os.environ.get("ROOP_OLLAMA_MODEL", "qwen2.5-coder:7b")


class OllamaAdapter:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.model: str = model
        self.timeout_seconds: float = timeout_seconds

    def chat(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        message: dict[str, Any] = data.get("message") or {}
        content: str = str(message.get("content") or "")
        return content

    def is_reachable(self) -> bool:
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
