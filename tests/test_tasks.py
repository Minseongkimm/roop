"""Tests for Phase 2 SQLite Task Manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import (
    Task,
    TaskStatus,
    TaskStore,
    TaskTransitionError,
)


def test_create_and_get_task(tmp_path: Path) -> None:
    # Arrange
    input_db: Path = tmp_path / "tasks.sqlite3"
    store: TaskStore = TaskStore(input_db)
    # Act
    created: Task = store.create_task(
        "scaffold agent",
        allow_paths=".agent/**",
        acceptance_criteria="`.agent/` exists",
        description="phase 2 create",
        feature_ids="chat",
        priority=10,
        verify_command="pytest -q",
    )
    actual: Task = store.get_task(created.id)
    # Assert
    assert actual.id == created.id
    assert actual.title == "scaffold agent"
    assert actual.status == TaskStatus.PENDING
    assert actual.allow_paths == ".agent/**"
    assert actual.retry_count == 0
    assert actual.acceptance_criteria == "`.agent/` exists"
    assert actual.description == "phase 2 create"
    assert actual.feature_ids == "chat"
    assert actual.priority == 10
    assert actual.verify_command == "pytest -q"
    assert actual.depends_on == ()
    assert actual.updated_at != ""


def test_list_and_update_status(tmp_path: Path) -> None:
    # Arrange
    store: TaskStore = TaskStore(tmp_path / "tasks.sqlite3")
    first: Task = store.create_task("one")
    store.create_task("two")
    # Act
    pending: list[Task] = store.list_tasks(status=TaskStatus.PENDING)
    updated: Task = store.update_status(first.id, TaskStatus.RUNNING)
    # Assert
    assert len(pending) == 2
    assert updated.status == TaskStatus.RUNNING
    assert store.next_pending() is not None


def test_increment_retry_and_missing_task(tmp_path: Path) -> None:
    # Arrange
    store: TaskStore = TaskStore(tmp_path / "tasks.sqlite3")
    task: Task = store.create_task("retry me")
    # Act
    retried: Task = store.increment_retry(task.id)
    # Assert
    assert retried.retry_count == 1
    with pytest.raises(KeyError):
        store.get_task(9999)


def test_transition_rejects_illegal_move(tmp_path: Path) -> None:
    # Arrange
    store: TaskStore = TaskStore(tmp_path / "tasks.sqlite3")
    task: Task = store.create_task("guard")
    # Act / Assert
    with pytest.raises(TaskTransitionError):
        store.transition(task.id, TaskStatus.DONE)


def test_next_runnable_respects_priority(tmp_path: Path) -> None:
    # Arrange
    store: TaskStore = TaskStore(tmp_path / "tasks.sqlite3")
    store.create_task("low", priority=50)
    store.create_task("high", priority=1)
    # Act
    actual: Task | None = store.next_runnable()
    # Assert
    assert actual is not None
    assert actual.title == "high"
    assert actual.priority == 1


def test_next_runnable_waits_on_dependencies(tmp_path: Path) -> None:
    # Arrange
    store: TaskStore = TaskStore(tmp_path / "tasks.sqlite3")
    first: Task = store.create_task("parent", priority=1)
    child: Task = store.create_task(
        "child",
        priority=1,
        depends_on=[first.id],
    )
    # Act
    runnable_before: Task | None = store.next_runnable()
    store.transition(first.id, TaskStatus.RUNNING)
    store.transition(first.id, TaskStatus.DONE)
    runnable_after: Task | None = store.next_runnable()
    # Assert
    assert runnable_before is not None
    assert runnable_before.id == first.id
    assert child.status == TaskStatus.PENDING
    assert runnable_after is not None
    assert runnable_after.id == child.id


def test_max_retries_auto_blocks(tmp_path: Path) -> None:
    # Arrange
    store: TaskStore = TaskStore(tmp_path / "tasks.sqlite3")
    task: Task = store.create_task("flaky", max_retries=2)
    store.transition(task.id, TaskStatus.RUNNING)
    # Act — first retry returns to pending
    after_first: Task = store.transition(task.id, TaskStatus.PENDING)
    store.transition(after_first.id, TaskStatus.RUNNING)
    after_second: Task = store.transition(after_first.id, TaskStatus.PENDING)
    # Assert
    assert after_first.status == TaskStatus.PENDING
    assert after_first.retry_count == 1
    assert after_second.status == TaskStatus.BLOCKED
    assert after_second.retry_count == 2
    assert "max retries" in after_second.block_reason


def test_tick_skips_unsatisfied_dependencies(tmp_path: Path) -> None:
    # Arrange
    db: Path = tmp_path / "tasks.sqlite3"
    store: TaskStore = TaskStore(db)
    parent: Task = store.create_task("parent")
    store.create_task("child", depends_on=[parent.id])
    store.transition(parent.id, TaskStatus.RUNNING)
    store.transition(parent.id, TaskStatus.BLOCKED, reason="manual")
    loop: OrchestratorLoop = OrchestratorLoop(store)
    # Act
    result: TickResult = loop.tick()
    # Assert
    assert result.did_work is False
    assert "dependencies" in result.message


def test_migrate_existing_database(tmp_path: Path) -> None:
    # Arrange — create legacy schema without Phase 2 columns
    db: Path = tmp_path / "legacy.sqlite3"
    import sqlite3

    connection: sqlite3.Connection = sqlite3.connect(db)
    connection.execute(
        """
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            allow_paths TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            acceptance_criteria TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute(
        """
        INSERT INTO tasks (title, status, allow_paths, retry_count, acceptance_criteria)
        VALUES ('legacy', 'pending', '.agent/**', 0, '')
        """
    )
    connection.commit()
    connection.close()
    # Act
    store: TaskStore = TaskStore(db)
    tasks: list[Task] = store.list_tasks()
    # Assert
    assert len(tasks) == 1
    assert tasks[0].title == "legacy"
    assert tasks[0].priority == 100
    assert tasks[0].depends_on == ()
