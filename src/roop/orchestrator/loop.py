from __future__ import annotations

from pathlib import Path

from roop.orchestrator.tasks import Task, TaskStore


class Orchestrator:
    """Phase 0 stub: one tick pops a task and marks it completed without model work."""

    def __init__(self, project_root: Path) -> None:
        self.project_root: Path = project_root.resolve()
        self.store: TaskStore = TaskStore(self.project_root / ".agent" / "roop" / "tasks.db")

    def enqueue(self, goal: str) -> int:
        return self.store.enqueue(str(self.project_root), goal)

    def tick(self) -> str:
        task: Task | None = self.store.pop_pending()
        if task is None:
            return "no pending tasks"
        # Later phases: Context Builder → model roles → Verifier.
        self.store.set_status(task.id, "completed")
        return f"completed task#{task.id}: {task.goal}"
