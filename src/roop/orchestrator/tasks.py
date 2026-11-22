from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Task:
    id: int
    project_path: str
    goal: str
    status: str
    retry_count: int


class TaskStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path: Path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_path TEXT NOT NULL,
              goal TEXT NOT NULL,
              status TEXT NOT NULL,
              retry_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        with self._connect() as connection:
            connection.execute(sql, params)
            connection.commit()

    def enqueue(self, project_path: str, goal: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO tasks (project_path, goal, status, retry_count) VALUES (?, ?, ?, 0)",
                (project_path, goal, "pending"),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def pop_pending(self) -> Optional[Task]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, project_path, goal, status, retry_count FROM tasks "
                "WHERE status = 'pending' ORDER BY id ASC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            task = Task(
                id=int(row[0]),
                project_path=str(row[1]),
                goal=str(row[2]),
                status=str(row[3]),
                retry_count=int(row[4]),
            )
            connection.execute(
                "UPDATE tasks SET status = 'running' WHERE id = ?",
                (task.id,),
            )
            connection.commit()
            return task

    def set_status(self, task_id: int, status: str) -> None:
        self._execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
