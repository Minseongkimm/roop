"""Tests for SQLite task CRUD."""

from __future__ import annotations

from pathlib import Path

import pytest

from roop.orchestrator.tasks import Task, TaskStatus, TaskStore


def test_create_and_get_task(tmp_path: Path) -> None:
    # Arrange
    input_db: Path = tmp_path / "tasks.sqlite3"
    store: TaskStore = TaskStore(input_db)
    # Act
    created: Task = store.create_task(
        "scaffold agent",
        allow_paths=".agent/**",
        acceptance_criteria="`.agent/` exists",
    )
    actual: Task = store.get_task(created.id)
    # Assert
    assert actual.id == created.id
    assert actual.title == "scaffold agent"
    assert actual.status == TaskStatus.PENDING
    assert actual.allow_paths == ".agent/**"
    assert actual.retry_count == 0
    assert actual.acceptance_criteria == "`.agent/` exists"


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
