"""Phase 0 analyze stub: detect stack hints and scaffold ``.agent/``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from roop.harness.fs_guard import WriteGuard

STACK_MARKERS: dict[str, str] = {
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "package.json": "node",
    "pubspec.yaml": "dart/flutter",
    "Cargo.toml": "rust",
    "go.mod": "go",
}


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    """Result of a stub analyze pass."""

    target_root: Path
    agent_root: Path
    detected_stacks: list[str]
    created_files: list[str]


def execute_analyze(target_path: Path) -> AnalyzeResult:
    target_root: Path = target_path.resolve()
    if not target_root.exists():
        raise FileNotFoundError(f"Target path does not exist: {target_root}")
    if not target_root.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {target_root}")
    detected_stacks: list[str] = _detect_stacks(target_root)
    guard: WriteGuard = WriteGuard(target_root)
    created_files: list[str] = _scaffold_agent_tree(
        guard=guard,
        detected_stacks=detected_stacks,
        target_root=target_root,
    )
    return AnalyzeResult(
        target_root=target_root,
        agent_root=guard.agent_root,
        detected_stacks=detected_stacks,
        created_files=created_files,
    )


def _detect_stacks(target_root: Path) -> list[str]:
    found: list[str] = []
    for marker, stack_name in STACK_MARKERS.items():
        if (target_root / marker).exists() and stack_name not in found:
            found.append(stack_name)
    return found


def _scaffold_agent_tree(
    *,
    guard: WriteGuard,
    detected_stacks: list[str],
    target_root: Path,
) -> list[str]:
    stack_line: str = ", ".join(detected_stacks) if detected_stacks else "unknown"
    files: dict[str, str] = {
        "AGENTS.md": (
            "# AGENTS\n\n"
            "Roop Phase 0 scaffold. Writes are limited to `.agent/**`.\n"
        ),
        "project/overview.md": (
            f"# Project overview\n\n"
            f"- Root: `{target_root}`\n"
            f"- Detected stacks: {stack_line}\n"
        ),
        "project/tech-stack.md": (
            f"# Tech stack\n\nDetected (stub): {stack_line}\n"
        ),
        "project/conventions.md": (
            "# Conventions\n\nFilled in by later Phase 1 analyzer.\n"
        ),
        "state/current-state.md": (
            "# Current state\n\nStatus: analyzed (stub)\n"
        ),
        "logs/.gitkeep": "",
    }
    created: list[str] = []
    for relative, content in files.items():
        agent_relative: Path = Path(guard.AGENT_DIR_NAME) / relative
        written: Path = guard.write_text(agent_relative, content)
        created.append(str(written.relative_to(guard.agent_root)))
    return created
