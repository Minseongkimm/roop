"""Base model plus one stronger OpenRouter fallback.

The base may be a local Ollama model (no base URL) or any OpenAI-compatible
endpoint. The key is read from the named environment variable at call time
and is never written into the command line or model settings.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from roop.engines.aider_engine import AiderEngine
from roop.engines.budget import (
    MAX_ATTEMPTS_PER_TASK,
    MAX_SECONDS_PER_ATTEMPT,
    MAX_USD_PER_RUN,
)

OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
DEFAULT_BASE_MODEL: str = "ollama_chat/qwen2.5-coder:7b"
DEFAULT_FALLBACK_MODEL: str = "qwen/qwen3-coder"
DEFAULT_FALLBACK_KEY_ENV: str = "OPENROUTER_API_KEY"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    base_url: str = ""
    key_env: str = ""

    @property
    def is_local(self) -> bool:
        return not self.base_url


@dataclass(frozen=True, slots=True)
class RouteConfig:
    base: ModelSpec
    fallback: ModelSpec | None = None
    max_attempts: int = MAX_ATTEMPTS_PER_TASK
    attempt_timeout_seconds: float = MAX_SECONDS_PER_ATTEMPT
    max_cost_usd: float = MAX_USD_PER_RUN

    def problem(self) -> str:
        if self.max_attempts < 1:
            return "max_attempts must be >= 1"
        if self.fallback is None:
            return ""
        if not self.fallback.base_url or not self.fallback.name:
            return "fallback base_url and model are required"
        if not os.environ.get(self.fallback.key_env, "").strip():
            return f"env {self.fallback.key_env} is empty"
        return ""


def local_attempts(config: RouteConfig) -> tuple[int, int]:
    """Return (base attempts, fallback attempts). The sum is ``max_attempts``."""
    if config.fallback is not None and config.max_attempts >= 2:
        return (config.max_attempts - 1, 1)
    return (config.max_attempts, 0)


def build_routed_engine(
    spec: ModelSpec,
    *,
    timeout_seconds: float,
    binary: str | None = None,
    runner: object | None = None,
) -> AiderEngine:
    if spec.is_local:
        model: str = spec.name
        if not model.startswith("ollama_chat/") and not model.startswith("ollama/"):
            model = f"ollama_chat/{model}"
        return AiderEngine(
            binary=binary,
            model=model,
            timeout_seconds=timeout_seconds,
            runner=runner,
            name=model,
        )
    aider_model: str = spec.name if spec.name.startswith("openai/") else f"openai/{spec.name}"
    lookup = None
    if "openrouter.ai" in spec.base_url:
        lookup = openrouter_lookup(spec.base_url, spec.key_env)
    return AiderEngine(
        binary=binary,
        model=aider_model,
        num_ctx=None,
        timeout_seconds=timeout_seconds,
        runner=runner,
        name=f"api:{spec.name}",
        extra_env={
            "OPENAI_API_BASE": spec.base_url.rstrip("/"),
            "OPENAI_API_KEY": os.environ.get(spec.key_env, ""),
            "NUM_RETRIES": "0",
            "LITELLM_NUM_RETRIES": "0",
        },
        usage_lookup=lookup,
    )


def fetch_openrouter_generation(
    generation_id: str,
    *,
    api_key: str,
    base_url: str,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """GET OpenRouter's generation record. The key stays in the header."""
    with httpx.Client(timeout=30.0, transport=transport) as client:
        response: httpx.Response = client.get(
            f"{base_url.rstrip('/')}/generation",
            params={"id": generation_id},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        payload: object = response.json()
    if not isinstance(payload, dict):
        return {}
    return payload


def openrouter_lookup(base_url: str, key_env: str) -> Callable[[str], dict[str, object]]:
    def lookup(generation_id: str) -> dict[str, object]:
        api_key: str = os.environ.get(key_env, "").strip()
        if not api_key or not generation_id:
            return {}
        return fetch_openrouter_generation(generation_id, api_key=api_key, base_url=base_url)

    return lookup
