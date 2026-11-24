"""One git worktree per eval task, sharing objects but not the working tree."""

from __future__ import annotations

import subprocess
from pathlib import Path


def ensure_task_worktree(workspace: Path, task_id: str) -> Path:
    """Return ``workspace/task_id`` as its own detached git worktree.

    A plain directory left by an older run is reused as-is. A missing directory
    is created with ``git worktree add`` from ``workspace/.roop-seed``.
    """
    if not task_id or task_id in {".", ".."} or "/" in task_id or "\\" in task_id:
        raise ValueError(f"invalid task id: {task_id!r}")
    workspace.mkdir(parents=True, exist_ok=True)
    task_dir: Path = workspace / task_id
    if task_dir.exists():
        return task_dir
    seed: Path = _ensure_seed(workspace)
    _git(["worktree", "add", "--detach", str(task_dir)], seed)
    return task_dir


def _ensure_seed(workspace: Path) -> Path:
    seed: Path = workspace / ".roop-seed"
    if (seed / ".git").is_dir():
        return seed
    seed.mkdir(parents=True, exist_ok=True)
    _git(["init", "-b", "main"], seed)
    _git(["commit", "--allow-empty", "-m", "roop seed"], seed)
    return seed


def _git(args: list[str], cwd: Path) -> None:
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", "-c", "user.name=roop", "-c", "user.email=roop@local", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail: str = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
