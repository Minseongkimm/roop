"""Aider adapter. The harness still decides whether the edit passed."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from roop.adapters.ollama import DEFAULT_MODEL, DEFAULT_NUM_CTX
from roop.engines.base import EngineGeneration, EngineRequest
from roop.engines.budget import MAX_SECONDS_PER_GENERATION

AIDER_MODEL: str = f"ollama_chat/{DEFAULT_MODEL}"
_STUB: str = '"""Empty implementation."""\n'
_OLLAMA_BASE: str = "http://127.0.0.1:11434"


def default_aider_binary() -> str:
    override: str = os.environ.get("ROOP_AIDER", "").strip()
    if override:
        return override
    candidate: Path = Path(__file__).resolve().parents[3] / ".venv-aider" / "bin" / "aider"
    if candidate.is_file():
        return str(candidate)
    return "aider"


def model_settings_text(*, model: str, temperature: float, num_ctx: int) -> str:
    return (
        f"- name: {model}\n"
        "  edit_format: whole\n"
        "  use_repo_map: false\n"
        f"  use_temperature: {temperature}\n"
        "  extra_params:\n"
        f"    num_ctx: {num_ctx}\n"
    )


def build_aider_command(
    request: EngineRequest,
    *,
    binary: str,
    model: str,
    settings_path: Path,
) -> list[str]:
    """Assemble one non-interactive whole-file Aider edit."""
    return [
        binary,
        "--model",
        model,
        "--edit-format",
        "whole",
        "--no-auto-commits",
        "--no-git",
        "--no-auto-test",
        "--yes-always",
        "--no-pretty",
        "--no-stream",
        "--no-analytics",
        "--no-check-update",
        "--test-cmd",
        request.test_command,
        "--model-settings-file",
        str(settings_path),
        "--message",
        request.prompt,
        *request.editable_files,
    ]


class AiderEngine:
    """Run Aider once per sample against the local Ollama model."""

    name: str = "aider"

    def __init__(
        self,
        *,
        binary: str | None = None,
        model: str = AIDER_MODEL,
        num_ctx: int = DEFAULT_NUM_CTX,
        timeout_seconds: float = MAX_SECONDS_PER_GENERATION,
        runner: object | None = None,
    ) -> None:
        self._binary: str = binary or default_aider_binary()
        self._model: str = model
        self._num_ctx: int = num_ctx
        self._timeout_seconds: float = timeout_seconds
        self._runner = runner or subprocess.run

    def generate(self, request: EngineRequest) -> EngineGeneration:
        before: dict[str, bytes] = _ensure_editable_files(request)
        settings: Path = request.workdir / ".agent" / "aider-model.yml"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            model_settings_text(
                model=self._model,
                temperature=request.temperature,
                num_ctx=self._num_ctx,
            ),
            encoding="utf-8",
        )
        command: list[str] = build_aider_command(
            request,
            binary=self._binary,
            model=self._model,
            settings_path=settings,
        )
        env: dict[str, str] = os.environ.copy()
        env["OLLAMA_API_BASE"] = _OLLAMA_BASE
        try:
            completed: subprocess.CompletedProcess[str] = self._runner(
                command,
                cwd=request.workdir,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return EngineGeneration(
                format_ok=False,
                format_error="timeout",
                raw_output=_output_text(exc.stdout, exc.stderr),
            )
        except OSError as exc:
            return EngineGeneration(format_ok=False, format_error=str(exc))
        raw: str = _output_text(completed.stdout, completed.stderr)
        if not _editable_files_changed(request, before):
            detail: str = (completed.stderr or completed.stdout or "no editable file changed").strip()
            return EngineGeneration(
                format_ok=False,
                format_error=detail[:300] or "no editable file changed",
                raw_output=raw,
            )
        return EngineGeneration(format_ok=True, raw_output=raw)


def _ensure_editable_files(request: EngineRequest) -> dict[str, bytes]:
    before: dict[str, bytes] = {}
    for relative in request.editable_files:
        path: Path = request.workdir / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_STUB, encoding="utf-8")
        if path.is_file():
            before[relative] = path.read_bytes()
    return before


def _editable_files_changed(request: EngineRequest, before: dict[str, bytes]) -> bool:
    for relative, original in before.items():
        path: Path = request.workdir / relative
        if not path.is_file() or path.read_bytes() != original:
            return True
    return False


def _output_text(stdout: object, stderr: object) -> str:
    out: str = stdout if isinstance(stdout, str) else ""
    err: str = stderr if isinstance(stderr, str) else ""
    return f"{out}\n{err}".strip()[:4000]
