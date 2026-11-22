"""Sequential orchestrator tick stub (one role decision placeholder)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from roop.orchestrator.tasks import Task, TaskStatus, TaskStore


@dataclass(frozen=True, slots=True)
class TickResult:
    """Outcome of a single orchestrator tick."""

    did_work: bool
    task_id: int | None
    message: str


class OrchestratorLoop:
    """Phase 0 placeholder: dequeue one pending task and mark it done."""

    def __init__(self, store: TaskStore) -> None:
        self._store: TaskStore = store

    @classmethod
    def from_database(cls, database_path: Path) -> OrchestratorLoop:
        return cls(TaskStore(database_path))

    def tick(self) -> TickResult:
        task: Task | None = self._store.next_pending()
        if task is None:
            return TickResult(did_work=False, task_id=None, message="queue empty")
        self._store.update_status(task.id, TaskStatus.RUNNING)
        # Phase 0: no model call — single sequential placeholder transition.
        self._store.update_status(task.id, TaskStatus.DONE)
        return TickResult(
            did_work=True,
            task_id=task.id,
            message=f"tick completed placeholder for task {task.id}: {task.title}",
        )

    def run_until_idle(self, *, max_ticks: int = 100) -> list[TickResult]:
        results: list[TickResult] = []
        for _ in range(max_ticks):
            result: TickResult = self.tick()
            results.append(result)
            if not result.did_work:
                break
        return results
