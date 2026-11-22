"""SQLite-backed task CRUD for the orchestrator queue."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable


class TaskStatus(StrEnum):
    """Task state machine values (Phase 0 subset)."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Task:
    """Immutable task row view."""

    id: int
    title: str
    status: TaskStatus
    allow_paths: str
    retry_count: int
    acceptance_criteria: str


class TaskStore:
    """Minimal SQLite queue: create, get, list, update status."""

    def __init__(self, database_path: Path) -> None:
        self._database_path: Path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def create_task(
        self,
        title: str,
        *,
        allow_paths: str = ".agent/**",
        acceptance_criteria: str = "",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                INSERT INTO tasks (title, status, allow_paths, retry_count, acceptance_criteria)
                VALUES (?, ?, ?, 0, ?)
                """,
                (title, status.value, allow_paths, acceptance_criteria),
            )
            task_id: int = int(cursor.lastrowid)
            connection.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> Task:
        with self._connect() as connection:
            row: sqlite3.Row | None = connection.execute(
                """
                SELECT id, title, status, allow_paths, retry_count, acceptance_criteria
                FROM tasks WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return self._row_to_task(row)

    def list_tasks(self, *, status: TaskStatus | None = None) -> list[Task]:
        query: str = (
            "SELECT id, title, status, allow_paths, retry_count, acceptance_criteria FROM tasks"
        )
        params: tuple[object, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status.value,)
        query += " ORDER BY id ASC"
        with self._connect() as connection:
            rows: Iterable[sqlite3.Row] = connection.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def update_status(self, task_id: int, status: TaskStatus) -> Task:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status.value, task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()
        return self.get_task(task_id)

    def increment_retry(self, task_id: int) -> Task:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                "UPDATE tasks SET retry_count = retry_count + 1 WHERE id = ?",
                (task_id,),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()
        return self.get_task(task_id)

    def next_pending(self) -> Task | None:
        pending: list[Task] = self.list_tasks(status=TaskStatus.PENDING)
        if not pending:
            return None
        return pending[0]

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    allow_paths TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    acceptance_criteria TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection: sqlite3.Connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=int(row["id"]),
            title=str(row["title"]),
            status=TaskStatus(str(row["status"])),
            allow_paths=str(row["allow_paths"]),
            retry_count=int(row["retry_count"]),
            acceptance_criteria=str(row["acceptance_criteria"]),
        )
