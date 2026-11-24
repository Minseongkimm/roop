"""One engine contract. The harness, not the engine, decides pass or fail."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EngineRequest:
    """Inputs every coding engine receives for one generation."""

    prompt: str
    editable_files: tuple[str, ...]
    test_command: str
    workdir: Path
    temperature: float = 0.0


@dataclass(frozen=True, slots=True)
class EngineGeneration:
    """Files the engine left in ``workdir``. Pass/fail is not this object's job."""

    format_ok: bool
    format_error: str = ""
    raw_output: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    provider_cost_usd: float = 0.0
    cache_cost_usd: float = 0.0
    cost_usd: float = 0.0


class CodingEngine(Protocol):
    """Generate one candidate edit. Do not grade the tests."""

    name: str

    def generate(self, request: EngineRequest) -> EngineGeneration:
        """Write editable files and return whether the edit had a usable form."""
