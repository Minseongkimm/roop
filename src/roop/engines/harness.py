"""Run an engine sample and grade it. Locked paths cannot count as a pass."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

from roop.engines.base import CodingEngine, EngineGeneration, EngineRequest
from roop.engines.budget import (
    BEST_OF_TEMPERATURES,
    MAX_GENERATIONS_PER_TASK,
    MAX_SECONDS_PER_TASK,
)

_IGNORED_PARTS: frozenset[str] = frozenset({".agent", ".git", "__pycache__"})
_TEST_TIMEOUT_SECONDS: float = 60.0


@dataclass(frozen=True, slots=True)
class SampleResult:
    index: int
    temperature: float
    passed: bool
    format_error: bool
    reason: str
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class BestOfResult:
    passed_at_1: bool
    passed_best: bool
    samples: tuple[SampleResult, ...]
    elapsed_seconds: float
    stop_reason: str


def run_best_of(
    engine: CodingEngine,
    *,
    prompt: str,
    editable_files: tuple[str, ...],
    test_command: str,
    workdir: Path,
    temperatures: tuple[float, ...] = BEST_OF_TEMPERATURES,
    max_generations: int = MAX_GENERATIONS_PER_TASK,
    max_seconds: float = MAX_SECONDS_PER_TASK,
    clock: Callable[[], float] | None = None,
) -> BestOfResult:
    """Try independent temperatures and keep the first sample that passes."""
    now: Callable[[], float] = clock or time.monotonic
    started: float = now()
    baseline: dict[str, bytes] = snapshot_tree(workdir)
    allowed: frozenset[str] = frozenset(_normalize(path) for path in editable_files)
    samples: list[SampleResult] = []
    stop_reason: str = "exhausted"
    for index, temperature in enumerate(temperatures[:max_generations]):
        if now() - started >= max_seconds:
            stop_reason = "time_cap"
            break
        restore_tree(workdir, baseline)
        sample_started: float = now()
        request: EngineRequest = EngineRequest(
            prompt=prompt,
            editable_files=editable_files,
            test_command=test_command,
            workdir=workdir,
            temperature=temperature,
        )
        try:
            generation: EngineGeneration = engine.generate(request)
        except Exception as exc:
            restore_tree(workdir, baseline)
            samples.append(
                SampleResult(
                    index=index,
                    temperature=temperature,
                    passed=False,
                    format_error=True,
                    reason=f"format: {type(exc).__name__}",
                    elapsed_seconds=round(now() - sample_started, 3),
                )
            )
            continue
        locked: tuple[str, ...] = changed_locked_paths(workdir, baseline, allowed)
        if locked:
            restore_tree(workdir, baseline)
            samples.append(
                SampleResult(
                    index=index,
                    temperature=temperature,
                    passed=False,
                    format_error=not generation.format_ok,
                    reason="locked path",
                    elapsed_seconds=round(now() - sample_started, 3),
                )
            )
            continue
        passed, reason = _grade(workdir, test_command, generation)
        samples.append(
            SampleResult(
                index=index,
                temperature=temperature,
                passed=passed,
                format_error=not generation.format_ok,
                reason="" if passed else reason,
                elapsed_seconds=round(now() - sample_started, 3),
            )
        )
        if passed:
            stop_reason = "pass"
            break
        restore_tree(workdir, baseline)
    elapsed: float = round(now() - started, 3)
    passed_at_1: bool = bool(samples and samples[0].passed)
    passed_best: bool = any(sample.passed for sample in samples)
    return BestOfResult(
        passed_at_1=passed_at_1,
        passed_best=passed_best,
        samples=tuple(samples),
        elapsed_seconds=elapsed,
        stop_reason=stop_reason,
    )


def snapshot_tree(root: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    if not root.exists():
        return found
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative: Path = path.relative_to(root)
        if any(part in _IGNORED_PARTS for part in relative.parts):
            continue
        found[relative.as_posix()] = path.read_bytes()
    return found


def restore_tree(root: Path, baseline: dict[str, bytes]) -> None:
    current: dict[str, bytes] = snapshot_tree(root)
    for relative in current:
        if relative in baseline:
            continue
        path: Path = root / relative
        if path.is_file():
            path.unlink()
    for relative, payload in baseline.items():
        path = root / relative
        if path.is_file() and path.read_bytes() == payload:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def changed_locked_paths(
    root: Path,
    baseline: dict[str, bytes],
    editable_files: frozenset[str],
) -> tuple[str, ...]:
    current: dict[str, bytes] = snapshot_tree(root)
    changed: list[str] = []
    for relative in sorted(set(baseline) | set(current)):
        if _normalize(relative) in editable_files:
            continue
        if baseline.get(relative) != current.get(relative):
            changed.append(relative)
    return tuple(changed)


def _grade(
    workdir: Path,
    test_command: str,
    generation: EngineGeneration,
) -> tuple[bool, str]:
    if not generation.format_ok:
        detail: str = generation.format_error or "format"
        return False, f"format: {detail}"[:200]
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            test_command,
            cwd=workdir,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if completed.returncode == 0:
        return True, ""
    return False, classify_failure(completed.stdout, completed.stderr)


def classify_failure(stdout: str, stderr: str) -> str:
    text: str = f"{stderr}\n{stdout}"
    if "SyntaxError" in text or "IndentationError" in text:
        return "syntax"
    if "ModuleNotFoundError" in text or "ImportError" in text:
        return "missing module"
    if "AssertionError" in text:
        return "assertion"
    if "TimeoutExpired" in text or "timeout" in text.lower():
        return "timeout"
    return "test failed"


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")
