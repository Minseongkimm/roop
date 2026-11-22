"""Hard-stop helper: snapshot workspace onto a ``wip/`` branch."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def commit_wip_branch(
    project_root: Path,
    *,
    reason: str,
    prefix: str = "wip/roop",
) -> str | None:
    """Create ``wip/roop-<stamp>``, commit current changes, return branch name.

    Returns None when the project is not a git repo or there is nothing to commit
    after staging. Never force-pushes and never switches the user away permanently
    without restoring the previous branch when possible.
    """
    root: Path = project_root.resolve()
    if not (root / ".git").exists() and not _is_git_worktree(root):
        return None
    stamp: str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    branch: str = f"{prefix}-{stamp}"
    previous: str = _run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "HEAD"
    status: str = _run_git(root, ["status", "--porcelain"])
    if not status.strip():
        return None
    _run_git(root, ["checkout", "-B", branch])
    _run_git(root, ["add", "-A"])
    message: str = f"wip: roop hard stop — {reason[:120]}"
    commit_code: int = _run_git_code(
        root,
        ["commit", "-m", message, "--no-verify"],
    )
    if commit_code != 0:
        _run_git(root, ["checkout", previous])
        return None
    return branch


def _is_git_worktree(root: Path) -> bool:
    code: int = _run_git_code(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0


def _run_git(root: Path, args: list[str]) -> str:
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or "").strip()


def _run_git_code(root: Path, args: list[str]) -> int:
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return int(completed.returncode)
