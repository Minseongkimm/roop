"""SQLite-backed Task Manager for the orchestrator queue (Phase 2)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterable

DEFAULT_PRIORITY: int = 100
DEFAULT_MAX_RETRIES: int = 4
DEFAULT_ALLOW_PATHS: str = ".agent/**"


class TaskStatus(StrEnum):
    """Task state machine values (Phase 2)."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.DONE, TaskStatus.BLOCKED, TaskStatus.PENDING}
    ),
    TaskStatus.BLOCKED: frozenset({TaskStatus.PENDING, TaskStatus.CANCELLED}),
    TaskStatus.DONE: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


class TaskTransitionError(ValueError):
    """Raised when a status transition is not allowed."""


@dataclass(frozen=True, slots=True)
class Task:
    """Immutable task row view."""

    id: int
    title: str
    status: TaskStatus
    allow_paths: str
    retry_count: int
    acceptance_criteria: str
    description: str = ""
    feature_ids: str = ""
    priority: int = DEFAULT_PRIORITY
    depends_on: tuple[int, ...] = ()
    verify_command: str = ""
    max_retries: int = DEFAULT_MAX_RETRIES
    updated_at: str = ""
    block_reason: str = ""
    last_failure_feedback: str = ""
    local_verify_failures: int = 0
    api_calls: int = 0
    estimated_cost_usd: float = 0.0
    outcome: str = ""
    last_model_output: str = ""
    transient_attempts: int = 0


class TaskStore:
    """SQLite queue: create, transition, dependencies, retries."""

    def __init__(self, database_path: Path) -> None:
        self._database_path: Path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def create_task(
        self,
        title: str,
        *,
        allow_paths: str = DEFAULT_ALLOW_PATHS,
        acceptance_criteria: str = "",
        status: TaskStatus = TaskStatus.PENDING,
        description: str = "",
        feature_ids: str = "",
        priority: int = DEFAULT_PRIORITY,
        depends_on: Iterable[int] | None = None,
        verify_command: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> Task:
        dependency_ids: tuple[int, ...] = tuple(
            sorted({int(item) for item in (depends_on or ())})
        )
        now: str = _utc_now()
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                INSERT INTO tasks (
                    title, status, allow_paths, retry_count, acceptance_criteria,
                    description, feature_ids, priority, depends_on, verify_command,
                    max_retries, updated_at, block_reason, last_failure_feedback,
                    local_verify_failures, api_calls, estimated_cost_usd, outcome
                )
                VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, '', '', 0, 0, 0, '')
                """,
                (
                    title,
                    status.value,
                    allow_paths,
                    acceptance_criteria,
                    description,
                    feature_ids,
                    priority,
                    json.dumps(list(dependency_ids)),
                    verify_command,
                    max_retries,
                    now,
                ),
            )
            task_id: int = int(cursor.lastrowid)
            connection.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> Task:
        with self._connect() as connection:
            row: sqlite3.Row | None = connection.execute(
                f"SELECT {_SELECT_COLUMNS} FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return self._row_to_task(row)

    def list_tasks(self, *, status: TaskStatus | None = None) -> list[Task]:
        query: str = f"SELECT {_SELECT_COLUMNS} FROM tasks"
        params: tuple[object, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status.value,)
        query += " ORDER BY priority ASC, id ASC"
        with self._connect() as connection:
            rows: Iterable[sqlite3.Row] = connection.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def update_status(self, task_id: int, status: TaskStatus) -> Task:
        """Legacy helper — prefer ``transition`` for guarded moves."""
        return self.transition(task_id, status)

    def transition(
        self,
        task_id: int,
        to_status: TaskStatus,
        *,
        reason: str = "",
        count_retry: bool = True,
    ) -> Task:
        task: Task = self.get_task(task_id)
        allowed: frozenset[TaskStatus] = ALLOWED_TRANSITIONS[task.status]
        if to_status not in allowed:
            raise TaskTransitionError(
                f"Cannot transition task {task_id} from {task.status.value} "
                f"to {to_status.value}"
            )
        final_status: TaskStatus = to_status
        retry_count: int = task.retry_count
        block_reason: str = task.block_reason
        if (
            task.status == TaskStatus.RUNNING
            and to_status == TaskStatus.PENDING
            and count_retry
        ):
            retry_count = task.retry_count + 1
            if retry_count >= task.max_retries:
                final_status = TaskStatus.BLOCKED
                block_reason = reason or "max retries exceeded"
        elif to_status == TaskStatus.BLOCKED:
            block_reason = reason or task.block_reason or "blocked"
        elif to_status == TaskStatus.PENDING and task.status == TaskStatus.BLOCKED:
            block_reason = ""
        elif to_status == TaskStatus.DONE:
            block_reason = ""
        now: str = _utc_now()
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE tasks
                SET status = ?, retry_count = ?, updated_at = ?, block_reason = ?
                WHERE id = ?
                """,
                (
                    final_status.value,
                    retry_count,
                    now,
                    block_reason,
                    task_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()
        return self.get_task(task_id)

    def increment_retry(self, task_id: int) -> Task:
        """Bump retry_count without changing status (compat helper)."""
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE tasks
                SET retry_count = retry_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (_utc_now(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()
        return self.get_task(task_id)

    def next_pending(self) -> Task | None:
        """Backward-compatible alias for ``next_runnable``."""
        return self.next_runnable()

    def next_runnable(self) -> Task | None:
        pending: list[Task] = self.list_tasks(status=TaskStatus.PENDING)
        for task in pending:
            if self._dependencies_satisfied(task):
                return task
        return None

    def has_pending_waiting_on_deps(self) -> bool:
        pending: list[Task] = self.list_tasks(status=TaskStatus.PENDING)
        if not pending:
            return False
        return self.next_runnable() is None

    def _dependencies_satisfied(self, task: Task) -> bool:
        for dependency_id in task.depends_on:
            try:
                dependency: Task = self.get_task(dependency_id)
            except KeyError:
                return False
            if dependency.status != TaskStatus.DONE:
                return False
        return True

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
                    acceptance_criteria TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    feature_ids TEXT NOT NULL DEFAULT '',
                    priority INTEGER NOT NULL DEFAULT 100,
                    depends_on TEXT NOT NULL DEFAULT '[]',
                    verify_command TEXT NOT NULL DEFAULT '',
                    max_retries INTEGER NOT NULL DEFAULT 4,
                    updated_at TEXT NOT NULL DEFAULT '',
                    block_reason TEXT NOT NULL DEFAULT '',
                    last_failure_feedback TEXT NOT NULL DEFAULT '',
                    local_verify_failures INTEGER NOT NULL DEFAULT 0,
                    api_calls INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    outcome TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._migrate_columns(connection)
            connection.commit()

    def _migrate_columns(self, connection: sqlite3.Connection) -> None:
        existing: set[str] = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }
        additions: dict[str, str] = {
            "description": "TEXT NOT NULL DEFAULT ''",
            "feature_ids": "TEXT NOT NULL DEFAULT ''",
            "priority": "INTEGER NOT NULL DEFAULT 100",
            "depends_on": "TEXT NOT NULL DEFAULT '[]'",
            "verify_command": "TEXT NOT NULL DEFAULT ''",
            "max_retries": "INTEGER NOT NULL DEFAULT 3",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
            "block_reason": "TEXT NOT NULL DEFAULT ''",
            "last_failure_feedback": "TEXT NOT NULL DEFAULT ''",
            "local_verify_failures": "INTEGER NOT NULL DEFAULT 0",
            "api_calls": "INTEGER NOT NULL DEFAULT 0",
            "estimated_cost_usd": "REAL NOT NULL DEFAULT 0",
            "outcome": "TEXT NOT NULL DEFAULT ''",
            "last_model_output": "TEXT NOT NULL DEFAULT ''",
            "transient_attempts": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, ddl in additions.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE tasks ADD COLUMN {name} {ddl}")

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
            description=str(row["description"] or ""),
            feature_ids=str(row["feature_ids"] or ""),
            priority=int(row["priority"] if row["priority"] is not None else DEFAULT_PRIORITY),
            depends_on=_parse_depends_on(row["depends_on"]),
            verify_command=str(row["verify_command"] or ""),
            max_retries=int(
                row["max_retries"]
                if row["max_retries"] is not None
                else DEFAULT_MAX_RETRIES
            ),
            updated_at=str(row["updated_at"] or ""),
            block_reason=str(row["block_reason"] or ""),
            last_failure_feedback=str(row["last_failure_feedback"] or ""),
            local_verify_failures=int(row["local_verify_failures"] or 0),
            api_calls=int(row["api_calls"] or 0),
            estimated_cost_usd=float(row["estimated_cost_usd"] or 0.0),
            outcome=str(row["outcome"] or ""),
            last_model_output=str(row["last_model_output"] or ""),
            transient_attempts=int(row["transient_attempts"] or 0),
        )

    def set_failure_feedback(self, task_id: int, feedback: str) -> None:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE tasks
                SET last_failure_feedback = ?
                WHERE id = ?
                """,
                (feedback, task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()

    def add_local_verify_failure(self, task_id: int) -> Task:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE tasks
                SET local_verify_failures = local_verify_failures + 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (_utc_now(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()
        return self.get_task(task_id)

    def add_usage(
        self,
        task_id: int,
        *,
        api_calls: int,
        estimated_cost_usd: float,
    ) -> Task:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE tasks
                SET api_calls = api_calls + ?,
                    estimated_cost_usd = estimated_cost_usd + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (int(api_calls), float(estimated_cost_usd), _utc_now(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()
        return self.get_task(task_id)

    def set_last_model_output(self, task_id: int, output: str) -> None:
        self._update_column(task_id, "last_model_output", output)

    def set_transient_attempts(self, task_id: int, attempts: int) -> None:
        self._update_column(task_id, "transient_attempts", int(attempts))

    def _update_column(self, task_id: int, column: str, value: object) -> None:
        if column not in {"last_model_output", "transient_attempts"}:
            raise ValueError(f"unsupported column: {column}")
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                f"UPDATE tasks SET {column} = ? WHERE id = ?",
                (value, task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()

    def set_outcome(self, task_id: int, outcome: str) -> None:
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE tasks
                SET outcome = ?, updated_at = ?
                WHERE id = ?
                """,
                (outcome, _utc_now(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Task not found: {task_id}")
            connection.commit()


_SELECT_COLUMNS: str = (
    "id, title, status, allow_paths, retry_count, acceptance_criteria, "
    "description, feature_ids, priority, depends_on, verify_command, "
    "max_retries, updated_at, block_reason, last_failure_feedback, "
    "local_verify_failures, api_calls, estimated_cost_usd, outcome, "
    "last_model_output, transient_attempts"
)


def task_difficulty(feature_ids: str) -> str:
    """Return easy, medium, hard, or unknown from a feature id list."""
    parts: list[str] = [item.strip() for item in feature_ids.split(",") if item.strip()]
    for item in parts:
        if item in {"easy", "medium", "hard"}:
            return item
    return "unknown"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_depends_on(raw: object) -> tuple[int, ...]:
    if raw is None or raw == "":
        return ()
    if isinstance(raw, str):
        try:
            payload: object = json.loads(raw)
        except json.JSONDecodeError:
            return ()
    else:
        payload = raw
    if not isinstance(payload, list):
        return ()
    result: list[int] = []
    for item in payload:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.isdigit():
            result.append(int(item))
    return tuple(sorted(set(result)))
