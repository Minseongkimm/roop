"""Token and dollar usage for one model attempt.

OpenRouter's reported cost wins when the response includes it. Otherwise a
small price table fills in from token counts. Provider price and cache cost
stay separate; ``cost_usd`` is their sum.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

# USD per token from the public OpenRouter models list:
# prompt, completion, input_cache_read.
# qwen3-coder-30b has no published cache price; cached tokens use the prompt
# price so a missing cache rate cannot hide spend from the run cap.
PRICE_PER_TOKEN: dict[str, tuple[float, float, float]] = {
    "qwen/qwen3-coder": (0.0000003, 0.000001, 0.0000001),
    "qwen/qwen3-coder-next": (0.00000012, 0.0000008, 0.00000007),
    "qwen/qwen3-coder-flash": (0.000000195, 0.000000975, 0.000000039),
    "qwen/qwen3-coder-30b-a3b-instruct": (0.00000007, 0.00000028, 0.00000007),
}
_GEN_ID_RE: re.Pattern[str] = re.compile(r"\b(gen-[A-Za-z0-9_-]+)\b")


@dataclass(frozen=True, slots=True)
class AttemptUsage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    provider_cost_usd: float = 0.0
    cache_cost_usd: float = 0.0
    cost_usd: float = 0.0
    generation_id: str = ""


def canonical_model(model: str) -> str:
    """Strip the Aider provider prefix so the price table can match."""
    name: str = (model or "").strip()
    if name.startswith("openai/"):
        return name[len("openai/") :]
    return name


def price_per_token(model: str) -> tuple[float, float, float] | None:
    """Return (input, output, cached input) USD per token, or None when free."""
    name: str = canonical_model(model)
    if name.startswith("ollama_chat/") or name.startswith("ollama/"):
        return None
    return PRICE_PER_TOKEN.get(name)


def usage_from_openrouter(model: str, payload: dict[str, object]) -> AttemptUsage:
    """Read a chat-completion body or a ``/generation`` object."""
    data: dict[str, object] = payload
    nested: object = payload.get("data")
    if isinstance(nested, dict) and "usage" in nested:
        data = nested
    reported: str = str(data.get("model") or model)
    generation_id: str = str(data.get("id") or "")
    usage: object = data.get("usage")
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total: float | None = None
    if isinstance(usage, dict):
        input_tokens = _as_int(usage.get("prompt_tokens"))
        output_tokens = _as_int(usage.get("completion_tokens"))
        details: object = usage.get("prompt_tokens_details")
        if isinstance(details, dict):
            cached_tokens = _as_int(details.get("cached_tokens"))
        if isinstance(usage.get("cost"), (int, float)):
            total = float(usage["cost"])
    elif isinstance(usage, (int, float)):
        input_tokens = _as_int(data.get("native_tokens_prompt") or data.get("tokens_prompt"))
        output_tokens = _as_int(data.get("native_tokens_completion") or data.get("tokens_completion"))
        cached_tokens = _as_int(data.get("native_tokens_cached"))
        total = float(usage)
    if input_tokens and cached_tokens > input_tokens:
        cached_tokens = input_tokens
    provider, cache = _split_cost(reported, input_tokens, output_tokens, cached_tokens, total)
    return AttemptUsage(
        model=reported,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        provider_cost_usd=provider,
        cache_cost_usd=cache,
        cost_usd=provider + cache,
        generation_id=generation_id,
    )


def usage_from_text(text: str, *, model: str) -> AttemptUsage:
    """Pull the last usage JSON object out of an engine log, if one is there."""
    payload: dict[str, object] | None = _extract_usage_payload(text or "")
    if payload is not None:
        usage: AttemptUsage = usage_from_openrouter(model, payload)
        if usage.generation_id:
            return usage
        found: str = _generation_id(text or "")
        if found:
            return AttemptUsage(
                model=usage.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_tokens=usage.cached_tokens,
                provider_cost_usd=usage.provider_cost_usd,
                cache_cost_usd=usage.cache_cost_usd,
                cost_usd=usage.cost_usd,
                generation_id=found,
            )
        return usage
    return AttemptUsage(model=model, generation_id=_generation_id(text or ""))


def _split_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    total: float | None,
) -> tuple[float, float]:
    rates: tuple[float, float, float] | None = price_per_token(model)
    provider: float = 0.0
    cache: float = 0.0
    if rates is not None:
        input_rate, output_rate, cache_rate = rates
        uncached: int = max(0, input_tokens - cached_tokens)
        provider = uncached * input_rate + output_tokens * output_rate
        cache = cached_tokens * cache_rate
    if total is None:
        return (provider, cache)
    weight: float = provider + cache
    if weight > 0:
        return (total * provider / weight, total * cache / weight)
    return (total, 0.0)


def _extract_usage_payload(text: str) -> dict[str, object] | None:
    decoder: json.JSONDecoder = json.JSONDecoder()
    found: dict[str, object] | None = None
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and _has_usage(obj):
            found = obj
    return found


def _has_usage(obj: dict[str, object]) -> bool:
    if "usage" in obj:
        return True
    data: object = obj.get("data")
    return isinstance(data, dict) and "usage" in data


def _generation_id(text: str) -> str:
    match: re.Match[str] | None = _GEN_ID_RE.search(text)
    return match.group(1) if match else ""


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)
