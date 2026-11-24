"""Escalation hook: an OpenAI-compatible API model behind the same Aider adapter.

Disabled by default. The key is read from the environment variable *named* in
the config; the key itself is never stored, logged, or written to settings.

Environment (all optional; CLI flags override):
  ROOP_ESCALATE=1                  enable
  ROOP_ESCALATE_BASE_URL           e.g. https://api.groq.com/openai/v1
  ROOP_ESCALATE_MODEL              e.g. qwen/qwen3.8-27b
  ROOP_ESCALATE_KEY_ENV            name of the env var holding the key (default ROOP_API_KEY)
  ROOP_ESCALATE_MAX_TOKENS         output cap per call (default 2048)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from roop.engines.aider_engine import AiderEngine
from roop.engines.budget import MAX_SECONDS_PER_GENERATION

PRESETS: dict[str, dict[str, str]] = {
    # Stand-in for a frontier API in cheap tests. Free tier: 30 RPM, ~1K OTPM.
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "qwen/qwen3.8-27b",
        "key_env": "GROQ_API_KEY",
        "max_tokens": "768",
    },
}


@dataclass(frozen=True, slots=True)
class EscalationConfig:
    enabled: bool = False
    base_url: str = ""
    model: str = ""
    key_env: str = "ROOP_API_KEY"
    max_tokens: int = 2048

    @property
    def label(self) -> str:
        return f"api:{self.model}" if self.model else "api"

    def has_key(self) -> bool:
        return bool(os.environ.get(self.key_env, "").strip())

    def problem(self) -> str:
        """Empty string when usable; otherwise why escalation cannot run."""
        if not self.enabled:
            return "disabled"
        if not self.base_url or not self.model:
            return "base_url and model are required"
        if not self.has_key():
            return f"env {self.key_env} is empty"
        return ""


def escalation_config(
    *,
    enabled: bool | None = None,
    preset: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    key_env: str | None = None,
    max_tokens: int | None = None,
    environ: dict[str, str] | None = None,
) -> EscalationConfig:
    env: dict[str, str] = dict(os.environ if environ is None else environ)
    chosen: dict[str, str] = dict(PRESETS.get((preset or "").strip().lower(), {}))
    if preset and not chosen:
        raise ValueError(f"unknown escalation preset: {preset} (known: {', '.join(PRESETS)})")
    on: bool = enabled if enabled is not None else (bool(preset) or env.get("ROOP_ESCALATE", "") in {"1", "true", "yes"})
    return EscalationConfig(
        enabled=on,
        base_url=(base_url or env.get("ROOP_ESCALATE_BASE_URL") or chosen.get("base_url", "")).rstrip("/"),
        model=model or env.get("ROOP_ESCALATE_MODEL") or chosen.get("model", ""),
        key_env=key_env or env.get("ROOP_ESCALATE_KEY_ENV") or chosen.get("key_env", "ROOP_API_KEY"),
        max_tokens=int(max_tokens or env.get("ROOP_ESCALATE_MAX_TOKENS") or chosen.get("max_tokens", "2048")),
    )


def build_escalation_engine(
    config: EscalationConfig,
    *,
    binary: str | None = None,
    timeout_seconds: float = MAX_SECONDS_PER_GENERATION,
    runner: object | None = None,
) -> AiderEngine | None:
    """Aider over an OpenAI-compatible endpoint, or None when not usable."""
    if config.problem():
        return None
    aider_model: str = f"openai/{config.model}"
    return AiderEngine(
        binary=binary,
        model=aider_model,
        num_ctx=None,
        max_tokens=config.max_tokens,
        timeout_seconds=timeout_seconds,
        runner=runner,
        name=config.label,
        extra_env={
            "OPENAI_API_BASE": config.base_url,
            "OPENAI_API_KEY": os.environ.get(config.key_env, ""),
            "NUM_RETRIES": "0",
            "LITELLM_NUM_RETRIES": "0",
        },
        extra_args=(),
    )
