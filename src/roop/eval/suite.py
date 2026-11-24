"""Load machine-checkable eval manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class EvalTask:
    id: str
    title: str
    description: str
    difficulty: str
    allow_paths: str
    acceptance_criteria: str
    verify_command: str
    protected_globs: tuple[str, ...] = ()
    golden_test: str = ""
    split: str = "practice"
    src_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvalSuite:
    name: str
    description: str
    path: Path
    tasks: tuple[EvalTask, ...] = field(default_factory=tuple)
    fixture: str = ""

    def by_difficulty(self, difficulty: str) -> list[EvalTask]:
        needle: str = difficulty.lower()
        return [item for item in self.tasks if item.difficulty.lower() == needle]

    def by_split(self, split: str, difficulty: str | None = None) -> list[EvalTask]:
        needle: str = split.lower()
        selected: list[EvalTask] = [
            item for item in self.tasks if item.split.lower() == needle
        ]
        if difficulty is None:
            return selected
        level: str = difficulty.lower()
        return [item for item in selected if item.difficulty.lower() == level]


def load_suite(manifest_path: Path) -> EvalSuite:
    path: Path = manifest_path.resolve()
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    tasks_raw: Any = payload.get("tasks") or []
    if not isinstance(tasks_raw, list):
        raise ValueError(f"invalid tasks list in {path}")
    default_verify: str = str(payload.get("verify_default") or "")
    tasks: list[EvalTask] = []
    for item in tasks_raw:
        if not isinstance(item, dict):
            continue
        task_id: str = str(item.get("id") or "").strip()
        title: str = str(item.get("title") or "").strip()
        if not task_id or not title:
            continue
        protected_raw: Any = item.get("protected_globs") or []
        protected: tuple[str, ...] = ()
        if isinstance(protected_raw, list):
            protected = tuple(str(entry) for entry in protected_raw if str(entry).strip())
        split: str = str(item.get("split") or "practice").strip().lower()
        if split not in {"practice", "heldout"}:
            raise ValueError(f"invalid split for {task_id}: {split}")
        src_raw: Any = item.get("src_files") or []
        src_files: tuple[str, ...] = ()
        if isinstance(src_raw, list):
            src_files = tuple(str(entry) for entry in src_raw if str(entry).strip())
        tasks.append(
            EvalTask(
                id=task_id,
                title=title,
                description=str(item.get("description") or ""),
                difficulty=str(item.get("difficulty") or "easy"),
                allow_paths=str(item.get("allow_paths") or "src/**"),
                acceptance_criteria=str(item.get("acceptance_criteria") or ""),
                verify_command=str(item.get("verify_command") or default_verify),
                protected_globs=protected,
                golden_test=str(item.get("golden_test") or ""),
                split=split,
                src_files=src_files,
            )
        )
    return EvalSuite(
        name=str(payload.get("name") or path.stem),
        description=str(payload.get("description") or ""),
        path=path,
        tasks=tuple(tasks),
        fixture=str(payload.get("fixture") or "").strip(),
    )


def default_suite_path() -> Path:
    return Path(__file__).resolve().parents[3] / "evals" / "v1" / "manifest.json"


def is_noop_verify_command(command: str) -> bool:
    """Return True when a verify command would always pass or is empty."""
    text: str = command.strip().lower()
    if not text:
        return True
    # strip simple shell no-ops
    compact: str = " ".join(text.split())
    if compact in {"true", ":", "/bin/true", "cmd /c exit 0"}:
        return True
    if compact.startswith("true ") or compact == "exit 0":
        return True
    return False
