from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from roop.adapters.ollama import OllamaAdapter


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def run_doctor(project_path: Path | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []
    git_path: str | None = shutil.which("git")
    results.append(
        CheckResult("git", git_path is not None, git_path or "not found")
    )
    rg_path: str | None = shutil.which("rg")
    results.append(
        CheckResult("ripgrep", rg_path is not None, rg_path or "not found (optional)")
    )
    adapter: OllamaAdapter = OllamaAdapter()
    ollama_ok: bool = adapter.is_reachable()
    results.append(
        CheckResult(
            "ollama",
            ollama_ok,
            f"{adapter.base_url} reachable" if ollama_ok else f"{adapter.base_url} unreachable (soft-fail)",
        )
    )
    if project_path is not None:
        root: Path = project_path.resolve()
        is_git: bool = (root / ".git").exists()
        if not is_git:
            try:
                completed = subprocess.run(
                    ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                is_git = completed.returncode == 0
            except Exception:
                is_git = False
        results.append(
            CheckResult(
                "project_git",
                is_git,
                str(root) if is_git else f"not a git repo: {root}",
            )
        )
    return results
