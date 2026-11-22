"""Orchestrator: task queue and sequential tick loop."""

from roop.orchestrator.tasks import Task, TaskStatus, TaskStore, TaskTransitionError

__all__ = [
    "OrchestratorLoop",
    "Task",
    "TaskStatus",
    "TaskStore",
    "TaskTransitionError",
    "TickResult",
]


def __getattr__(name: str) -> object:
    if name in {"OrchestratorLoop", "TickResult"}:
        from roop.orchestrator.loop import OrchestratorLoop, TickResult

        exports: dict[str, object] = {
            "OrchestratorLoop": OrchestratorLoop,
            "TickResult": TickResult,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
