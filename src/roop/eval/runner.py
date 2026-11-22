"""Enqueue and optionally execute an eval suite into a dedicated SQLite DB."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from roop.context.roles import AgentRole
from roop.eval.suite import EvalSuite, EvalTask, load_suite
from roop.eval.tamper import TamperGuard, TamperResult
from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import Task, TaskStore


@dataclass(frozen=True, slots=True)
class EvalEnqueueResult:
    suite_name: str
    database_path: Path
    task_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class EvalRunResult:
    suite_name: str
    enqueued: EvalEnqueueResult
    tick_results: tuple[TickResult, ...]
    tamper: TamperResult | None = None


def enqueue_suite(
    *,
    project_root: Path,
    suite: EvalSuite,
    database_path: Path,
    task_ids: list[str] | None = None,
) -> EvalEnqueueResult:
    store: TaskStore = TaskStore(database_path)
    selected: list[EvalTask] = list(suite.tasks)
    if task_ids:
        wanted: set[str] = set(task_ids)
        selected = [item for item in selected if item.id in wanted]
    created: list[int] = []
    for item in selected:
        task: Task = store.create_task(
            f"[eval:{item.id}] {item.title}",
            description=item.description,
            feature_ids=f"eval,{item.difficulty},{item.id}",
            allow_paths=item.allow_paths,
            acceptance_criteria=item.acceptance_criteria,
            verify_command=item.verify_command,
            priority=10 if item.difficulty == "easy" else 20,
        )
        created.append(task.id)
    return EvalEnqueueResult(
        suite_name=suite.name,
        database_path=database_path,
        task_ids=tuple(created),
    )


def run_suite(
    *,
    project_root: Path,
    suite_path: Path,
    database_path: Path,
    task_ids: list[str] | None = None,
    execute: bool = False,
    dry_run: bool = False,
    max_ticks: int = 100,
    protected_snapshot: bool = True,
) -> EvalRunResult:
    suite: EvalSuite = load_suite(suite_path)
    enqueued: EvalEnqueueResult = enqueue_suite(
        project_root=project_root,
        suite=suite,
        database_path=database_path,
        task_ids=task_ids,
    )
    tamper_result: TamperResult | None = None
    guard: TamperGuard | None = None
    if protected_snapshot:
        protected: list[str] = []
        for item in suite.tasks:
            if task_ids and item.id not in task_ids:
                continue
            protected.extend(item.protected_globs)
        guard = TamperGuard(project_root, tuple(dict.fromkeys(protected)))
        guard.snapshot()
    tick_results: list[TickResult] = []
    if execute:
        loop: OrchestratorLoop = OrchestratorLoop.from_database(
            database_path,
            project_root=project_root,
            role=AgentRole.CODER,
            execute=True,
            dry_run=dry_run,
        )
        tick_results = loop.run_until_idle(max_ticks=max_ticks)
        if guard is not None:
            tamper_result = guard.check()
    return EvalRunResult(
        suite_name=suite.name,
        enqueued=enqueued,
        tick_results=tuple(tick_results),
        tamper=tamper_result,
    )
