from __future__ import annotations

from pathlib import Path

from roop.orchestrator.loop import Orchestrator


def test_enqueue_and_tick(tmp_path: Path) -> None:
    orchestrator: Orchestrator = Orchestrator(tmp_path)
    task_id: int = orchestrator.enqueue("demo goal")
    assert task_id >= 1
    message: str = orchestrator.tick()
    assert "completed task#" in message
    assert orchestrator.tick() == "no pending tasks"
