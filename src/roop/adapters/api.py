"""Cheap OpenAI-compatible API client for verification fallback.

The key is read only from the environment. Nothing here embeds a secret.
"""

from __future__ import annotations

import os
from typing import Sequence

import httpx

from roop.adapters.model import ChatMessage, ModelResponse

DEFAULT_API_MODEL: str = "gpt-4o-mini"
DEFAULT_API_BASE_URL: str = "https://api.openai.com/v1"
API_KEY_ENV: str = "ROOP_API_KEY"
API_KEY_FALLBACK_ENV: str = "OPENAI_API_KEY"
API_MODEL_ENV: str = "ROOP_API_MODEL"
API_BASE_ENV: str = "ROOP_API_BASE_URL"
LOCAL_VERIFY_FAILURES_BEFORE_API: int = 2

# Published gpt-4o-mini list price, USD per token. Used as an estimate.
_INPUT_USD_PER_TOKEN: float = 0.15 / 1_000_000
_OUTPUT_USD_PER_TOKEN: float = 0.60 / 1_000_000


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimate USD from token counts using the default cheap-model rates."""
    safe_input: int = max(0, input_tokens)
    safe_output: int = max(0, output_tokens)
    return (safe_input * _INPUT_USD_PER_TOKEN) + (safe_output * _OUTPUT_USD_PER_TOKEN)


def read_api_key() -> str:
    """Return the API key from the environment, or an empty string."""
    primary: str = os.environ.get(API_KEY_ENV, "").strip()
    if primary:
        return primary
    return os.environ.get(API_KEY_FALLBACK_ENV, "").strip()


def should_hand_off_to_api(
    *,
    local_verify_failures: int,
    dry_run: bool,
    difficulty: str = "",
) -> bool:
    """Hand off only hard tasks, after repeated local verification failures."""
    if dry_run or difficulty != "hard":
        return False
    return local_verify_failures >= LOCAL_VERIFY_FAILURES_BEFORE_API


class ApiClient:
    """Chat client for one cheap API model. Counts calls and estimated cost."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_API_MODEL,
        base_url: str = DEFAULT_API_BASE_URL,
        timeout_seconds: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key: str = api_key
        self._model: str = model
        self._base_url: str = base_url.rstrip("/")
        self._timeout_seconds: float = timeout_seconds
        self._transport: httpx.BaseTransport | None = transport
        self.calls: int = 0
        self.estimated_cost_usd: float = 0.0

    def is_available(self) -> bool:
        return bool(self._api_key)

    def list_models(self) -> list[str]:
        if not self._api_key:
            return []
        return [self._model]

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        selected: str = model or self._model
        self.calls += 1
        body: dict[str, object] = {
            "model": selected,
            "messages": [
                {"role": item.role, "content": item.content} for item in messages
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        headers: dict[str, str] = {"Authorization": f"Bearer {self._api_key}"}
        with httpx.Client(
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            response: httpx.Response = client.post(
                f"{self._base_url}/chat/completions",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            payload: object = response.json()
        if not isinstance(payload, dict):
            raise ValueError("API response was not a JSON object")
        content: str = _message_content(payload)
        input_tokens, output_tokens = _token_counts(payload, messages, content)
        cost: float = estimate_cost_usd(input_tokens, output_tokens)
        self.estimated_cost_usd += cost
        responded_model: object = payload.get("model")
        return ModelResponse(
            content=content,
            model=responded_model if isinstance(responded_model, str) else selected,
            done=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            provider="api",
        )


def api_client_from_env() -> ApiClient | None:
    """Build a client from env vars, or return None when no key is set."""
    key: str = read_api_key()
    if not key:
        return None
    model: str = os.environ.get(API_MODEL_ENV, "").strip() or DEFAULT_API_MODEL
    base_url: str = os.environ.get(API_BASE_ENV, "").strip() or DEFAULT_API_BASE_URL
    return ApiClient(api_key=key, model=model, base_url=base_url)


def _message_content(payload: dict[str, object]) -> str:
    choices: object = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first: object = choices[0]
    if not isinstance(first, dict):
        return ""
    message: object = first.get("message")
    if not isinstance(message, dict):
        return ""
    content: object = message.get("content")
    if isinstance(content, str):
        return content
    return ""


def _token_counts(
    payload: dict[str, object],
    messages: Sequence[ChatMessage],
    content: str,
) -> tuple[int, int]:
    usage: object = payload.get("usage")
    if isinstance(usage, dict):
        prompt: object = usage.get("prompt_tokens")
        completion: object = usage.get("completion_tokens")
        if isinstance(prompt, int) and isinstance(completion, int):
            return prompt, completion
    input_tokens: int = _estimate_text(
        "\n".join(item.content for item in messages)
    )
    output_tokens: int = _estimate_text(content)
    return input_tokens, output_tokens


def _estimate_text(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)
