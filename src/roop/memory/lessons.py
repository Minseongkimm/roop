"""Experience memory — append verified lessons only (Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from roop.harness.fs_guard import WriteGuard


@dataclass(frozen=True, slots=True)
class Lesson:
    """One verified lesson line."""

    task_id: int
    summary: str
    evidence: str


class LessonStore:
    """Append-only lessons under ``.agent/memory/lessons.md``."""

    def __init__(self, project_root: Path) -> None:
        self._guard: WriteGuard = WriteGuard(project_root.resolve())

    @property
    def lessons_path(self) -> Path:
        return self._guard.agent_root / "memory" / "lessons.md"

    def append(self, lesson: Lesson) -> Path:
        cleaned: str = " ".join(lesson.summary.strip().split())
        if not cleaned:
            raise ValueError("empty lesson")
        stamp: str = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        line: str = (
            f"- [{stamp}] task#{lesson.task_id}: {cleaned} "
            f"(evidence: {lesson.evidence.strip()[:300]})\n"
        )
        existing: str = ""
        if self.lessons_path.is_file():
            existing = self.lessons_path.read_text(encoding="utf-8")
        if not existing.strip():
            existing = "# Lessons\n\nVerified experiences only.\n\n"
        relative: Path = Path(WriteGuard.AGENT_DIR_NAME) / "memory" / "lessons.md"
        return self._guard.write_text(relative, existing + line)

    def read_matching(self, *, query: str, limit: int = 5) -> str:
        if not self.lessons_path.is_file() or not query.strip():
            return ""
        needle: str = query.lower()
        hits: list[str] = []
        for line in self.lessons_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- ") and needle in line.lower():
                hits.append(line)
            if len(hits) >= limit:
                break
        return "\n".join(hits)
