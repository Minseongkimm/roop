"""Run the failure-aware retry loop over a split and write results + one summary line."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from roop.engines.base import CodingEngine
from roop.engines.retry_loop import (
    MAX_LOCAL_ATTEMPTS,
    MAX_SECONDS_PER_RETRY_TASK,
    AttemptRecord,
    RetryResult,
    run_retry_loop,
)
from roop.engines.roop_engine import task_prompt
from roop.eval.runner import install_fixture, install_golden_tests
from roop.eval.suite import EvalSuite, EvalTask
from roop.eval.worktree import ensure_task_worktree


def result_row(engine_name: str, task: EvalTask, outcome: RetryResult) -> dict[str, object]:
    return {
        "engine": engine_name,
        "difficulty": task.difficulty,
        "task_id": task.id,
        "first_pass": outcome.first_pass,
        "local_eventual": outcome.local_eventual,
        "eventual": outcome.eventual,
        "attempts_used": outcome.attempts_used,
        "local_attempts": outcome.local_attempts,
        "escalated": outcome.escalated,
        "escalation_solved": outcome.escalation_solved,
        "kinds": list(outcome.kinds),
        "stop_reason": outcome.stop_reason,
        "elapsed_seconds": outcome.elapsed_seconds,
        "cost_usd": outcome.cost_usd,
        "attempts": [
            {key: value for key, value in asdict(item).items() if key != "excerpt"}
            for item in outcome.attempts
        ],
    }


def summarize(rows: list[dict[str, object]]) -> str:
    n: int = len(rows)

    def count(key: str) -> int:
        return sum(1 for row in rows if row.get(key))

    def pct(k: int) -> str:
        return f"{(100 * k / n):.0f}%" if n else "-"

    first: int = count("first_pass")
    local: int = count("local_eventual")
    final: int = count("eventual")
    escalated: int = count("escalated")
    solved: int = count("escalation_solved")
    attempts: int = sum(int(row.get("local_attempts") or 0) for row in rows)
    avg: str = f"{attempts / n:.2f}" if n else "-"
    return (
        f"tasks={n} first-pass {first}/{n} ({pct(first)}) | "
        f"local eventual {local}/{n} ({pct(local)}) | "
        f"eventual incl. API {final}/{n} ({pct(final)}) | "
        f"escalated {escalated} solved {solved} | avg local attempts {avg}"
    )


def failure_kind_counts(rows: list[dict[str, object]]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for row in rows:
        for kind in row.get("kinds") or []:
            counts[str(kind)] = counts.get(str(kind), 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def run_retry_eval(
    *,
    engine: CodingEngine,
    suite: EvalSuite,
    workspace: Path,
    split: str = "heldout",
    difficulty: str | None = None,
    task_ids: list[str] | None = None,
    max_local_attempts: int = MAX_LOCAL_ATTEMPTS,
    escalation_engine: CodingEngine | None = None,
    escalation_attempts: int = 1,
    max_seconds: float = MAX_SECONDS_PER_RETRY_TASK,
    max_cost_usd: float | None = None,
    on_attempt: Callable[[str, AttemptRecord], None] | None = None,
) -> list[dict[str, object]]:
    """Resumable: tasks already in results.jsonl are skipped.

    ``max_cost_usd`` stops the queue from starting another task. The task that
    crossed the cap still finishes, and its ``stop_reason`` stays its own.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    results_path: Path = workspace / "results.jsonl"
    done: dict[str, dict[str, object]] = _load(results_path)
    selected: list[EvalTask] = suite.by_split(split, difficulty)
    if task_ids:
        wanted: set[str] = set(task_ids)
        selected = [task for task in selected if task.id in wanted]
    spent: float = sum(float(row.get("cost_usd") or 0) for row in done.values())
    skipped: list[str] = []
    run_stop: str = ""
    for task in selected:
        if task.id in done:
            continue
        if max_cost_usd is not None and spent >= max_cost_usd:
            run_stop = "cost_cap"
            skipped.append(task.id)
            continue
        task_dir: Path = ensure_task_worktree(workspace, task.id)
        install_fixture(project_root=task_dir, suite=suite)
        install_golden_tests(project_root=task_dir, suite=suite, task_ids=[task.id])
        outcome: RetryResult = run_retry_loop(
            engine,
            prompt=task_prompt(task.description, task.src_files, task.verify_command),
            editable_files=task.src_files,
            test_command=task.verify_command,
            workdir=task_dir,
            max_local_attempts=max_local_attempts,
            escalation_engine=escalation_engine,
            escalation_attempts=escalation_attempts,
            max_seconds=max_seconds,
            on_attempt=(lambda record, tid=task.id: on_attempt(tid, record)) if on_attempt else None,
        )
        row: dict[str, object] = result_row(engine.name, task, outcome)
        done[task.id] = row
        spent += float(outcome.cost_usd)
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    ordered: list[dict[str, object]] = [done[task.id] for task in selected if task.id in done]
    lines: list[str] = [summarize(ordered)]
    kinds: list[tuple[str, int]] = failure_kind_counts(ordered)
    if kinds:
        lines.append("failure kinds: " + ", ".join(f"{kind} {count}" for kind, count in kinds))
    if run_stop:
        lines.append(
            f"run_stop: {run_stop} spent_usd={spent:.6f} skipped={','.join(skipped) or '-'}"
        )
    (workspace / "run_state.json").write_text(
        json.dumps(
            {
                "stop_reason": run_stop or "completed",
                "spent_usd": round(spent, 10),
                "skipped": skipped,
                "max_cost_usd": max_cost_usd,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    for row in ordered:
        mark: str = "PASS" if row["eventual"] else "FAIL"
        lines.append(
            f"{mark}\t{row['task_id']}\tfirst={int(bool(row['first_pass']))}\t"
            f"local={int(bool(row['local_eventual']))}\tapi={int(bool(row['escalation_solved']))}\t"
            f"attempts={row['attempts_used']}\tstop={row.get('stop_reason')}\t"
            f"kinds={','.join(row.get('kinds') or []) or '-'}"
        )
    (workspace / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ordered


def _load(path: Path) -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row: dict[str, object] = json.loads(line)
            if row.get("task_id"):
                found[str(row["task_id"])] = row
    return found
