"""Environment doctor checks for Phase 0."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from roop.adapters.ollama import OllamaClient


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    """Single doctor check result."""

    name: str
    is_ok: bool
    detail: str


def execute_doctor(
    *,
    target_path: Path | None = None,
    ollama_client: OllamaClient | None = None,
) -> list[DoctorCheck]:
    client: OllamaClient = ollama_client or OllamaClient()
    checks: list[DoctorCheck] = [
        _check_command("git", ["git", "--version"]),
        _check_command("rg", ["rg", "--version"]),
        _check_ollama(client),
    ]
    if target_path is not None:
        checks.append(_check_git_repo(target_path))
    return checks


def _check_command(name: str, argv: list[str]) -> DoctorCheck:
    binary: str | None = shutil.which(argv[0])
    if binary is None:
        return DoctorCheck(name=name, is_ok=False, detail=f"{argv[0]} not found on PATH")
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as err:
        return DoctorCheck(name=name, is_ok=False, detail=str(err))
    detail: str = (completed.stdout or completed.stderr or "").strip().splitlines()[0]
    return DoctorCheck(name=name, is_ok=completed.returncode == 0, detail=detail)


def _check_ollama(client: OllamaClient) -> DoctorCheck:
    if not client.is_available():
        return DoctorCheck(
            name="ollama",
            is_ok=False,
            detail="no response from http://127.0.0.1:11434/api/tags",
        )
    models: list[str] = client.list_models()
    if models:
        preview: str = ", ".join(models[:5])
        return DoctorCheck(name="ollama", is_ok=True, detail=f"ok — models: {preview}")
    return DoctorCheck(
        name="ollama",
        is_ok=True,
        detail="ok — server up, no models pulled yet",
    )


def _check_git_repo(target_path: Path) -> DoctorCheck:
    resolved: Path = target_path.resolve()
    if not resolved.exists():
        return DoctorCheck(name="target-git", is_ok=False, detail=f"missing path: {resolved}")
    git_dir: Path = resolved / ".git"
    if git_dir.exists():
        return DoctorCheck(name="target-git", is_ok=True, detail=f"git repo at {resolved}")
    return DoctorCheck(
        name="target-git",
        is_ok=False,
        detail=f"not a git repo: {resolved}",
    )
