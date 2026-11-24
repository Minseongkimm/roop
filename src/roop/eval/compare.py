"""Run one engine over a split and write a Best-of-5 scorecard."""

from __future__ import annotations

import json
from pathlib import Path

from roop.engines.aider_engine import AiderEngine
from roop.engines.base import CodingEngine
from roop.engines.budget import (
    BEST_OF_TEMPERATURES,
    MAX_GENERATIONS_PER_TASK,
    MAX_SECONDS_PER_TASK,
)
from roop.engines.harness import BestOfResult, run_best_of
from roop.engines.roop_engine import RoopEngine, task_prompt
from roop.eval.best_score import (
    BestOfScoreRow,
    BestOfTaskResult,
    aggregate_best_of,
    render_best_of_scorecard,
    top_failure_reasons,
)
from roop.eval.runner import install_fixture, install_golden_tests
from roop.eval.suite import EvalSuite, EvalTask, load_suite


def build_engine(name: str) -> CodingEngine:
    key: str = name.strip().lower()
    if key == "roop":
        return RoopEngine()
    if key == "aider":
        return AiderEngine()
    raise ValueError(f"unknown engine: {name}")


def run_compare(
    *,
    engine: CodingEngine,
    suite: EvalSuite,
    workspace: Path,
    split: str = "heldout",
    difficulty: str | None = None,
    max_generations: int = MAX_GENERATIONS_PER_TASK,
    max_seconds: float = MAX_SECONDS_PER_TASK,
) -> list[BestOfTaskResult]:
    """Grade each selected task independently. Existing jsonl rows are kept."""
    workspace.mkdir(parents=True, exist_ok=True)
    results_path: Path = workspace / "results.jsonl"
    done: dict[str, BestOfTaskResult] = _load_results(results_path)
    selected: list[EvalTask] = suite.by_split(split, difficulty)
    for task in selected:
        if task.id in done:
            continue
        task_dir: Path = workspace / task.id
        task_dir.mkdir(parents=True, exist_ok=True)
        install_fixture(project_root=task_dir, suite=suite)
        install_golden_tests(
            project_root=task_dir,
            suite=suite,
            task_ids=[task.id],
        )
        outcome: BestOfResult = run_best_of(
            engine,
            prompt=task_prompt(task.description, task.src_files, task.verify_command),
            editable_files=task.src_files,
            test_command=task.verify_command,
            workdir=task_dir,
            temperatures=BEST_OF_TEMPERATURES,
            max_generations=max_generations,
            max_seconds=max_seconds,
        )
        result: BestOfTaskResult = _task_result(engine.name, task, outcome)
        done[task.id] = result
        _append_result(results_path, result)
    ordered: list[BestOfTaskResult] = [done[task.id] for task in selected if task.id in done]
    rows: list[BestOfScoreRow] = aggregate_best_of(ordered)
    rendered: str = render_best_of_scorecard(rows)
    reasons: list[tuple[str, int]] = top_failure_reasons(ordered)
    reason_lines: str = "\n".join(f"{count}\t{reason}" for reason, count in reasons)
    (workspace / "scorecard.txt").write_text(
        rendered + ("\n\nfailures\n" + reason_lines if reason_lines else "") + "\n",
        encoding="utf-8",
    )
    return ordered


def _task_result(engine_name: str, task: EvalTask, outcome: BestOfResult) -> BestOfTaskResult:
    reason: str = ""
    if not outcome.passed_best:
        failed: list[str] = [sample.reason for sample in outcome.samples if sample.reason]
        reason = failed[-1] if failed else outcome.stop_reason
    return BestOfTaskResult(
        engine=engine_name,
        difficulty=task.difficulty,
        task_id=task.id,
        passed_at_1=outcome.passed_at_1,
        passed_best=outcome.passed_best,
        generations=len(outcome.samples),
        elapsed_seconds=outcome.elapsed_seconds,
        format_errors=sum(1 for sample in outcome.samples if sample.format_error),
        failure_reason=reason,
    )


def _append_result(path: Path, result: BestOfTaskResult) -> None:
    payload: dict[str, object] = {
        "engine": result.engine,
        "difficulty": result.difficulty,
        "task_id": result.task_id,
        "passed_at_1": result.passed_at_1,
        "passed_best": result.passed_best,
        "generations": result.generations,
        "elapsed_seconds": result.elapsed_seconds,
        "format_errors": result.format_errors,
        "failure_reason": result.failure_reason,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _load_results(path: Path) -> dict[str, BestOfTaskResult]:
    if not path.is_file():
        return {}
    found: dict[str, BestOfTaskResult] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: dict[str, object] = json.loads(line)
        task_id: str = str(row.get("task_id") or "")
        if not task_id:
            continue
        found[task_id] = BestOfTaskResult(
            engine=str(row.get("engine") or ""),
            difficulty=str(row.get("difficulty") or ""),
            task_id=task_id,
            passed_at_1=bool(row.get("passed_at_1")),
            passed_best=bool(row.get("passed_best")),
            generations=int(row.get("generations") or 0),
            elapsed_seconds=float(row.get("elapsed_seconds") or 0.0),
            format_errors=int(row.get("format_errors") or 0),
            failure_reason=str(row.get("failure_reason") or ""),
        )
    return found


def load_compare_suite(path: Path | None) -> EvalSuite:
    from roop.eval.suite import default_suite_path

    return load_suite(path or default_suite_path())
