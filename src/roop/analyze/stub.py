from __future__ import annotations

from pathlib import Path

from roop.harness.fs_guard import WriteGuard

SKELETON_FILES: dict[str, str] = {
    "AGENTS.md": "# Agents\n\nRoop Phase 0 scaffold. Fill via full analyzer later.\n",
    "project/overview.md": "# Overview\n\nUnknown until full analyze.\n",
    "project/tech-stack.md": "# Tech stack\n\nUnknown until full analyze.\n",
    "project/conventions.md": "# Conventions\n\nUnknown until full analyze.\n",
    "state/current-state.md": "# Current state\n\nPhase 0 scaffold created.\n",
    "memory/lessons.md": "# Lessons\n\n(empty)\n",
}


def scaffold_agent_dir(project_root: Path) -> list[Path]:
    guard: WriteGuard = WriteGuard(project_root)
    written: list[Path] = []
    for relative, content in SKELETON_FILES.items():
        target: Path = guard.agent_root / relative
        guard.write_text(target, content)
        written.append(target)
    logs_dir: Path = guard.agent_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return written
