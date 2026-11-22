"""Prove each fixed golden test accepts a reference solution and rejects an empty one.

The score is per task, matching the eval scorecard: 10 GREEN or 0 GREEN.
Reference sources live under evals/v1/reference/<task-id>/src and are never
installed into an eval scratch.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from roop.eval.suite import EvalTask, default_suite_path, load_suite

REFERENCE_ROOT: Path = (
    Path(__file__).resolve().parents[1] / "evals" / "v1" / "reference"
)


def test_easy_and_medium_oracles_score_ten_and_zero() -> None:
    suite = load_suite(default_suite_path())
    for difficulty in ("easy", "medium"):
        tasks: list[EvalTask] = suite.by_difficulty(difficulty)
        assert len(tasks) == 10
        reference_score, reference_failures = _score_tasks(suite.path.parent, tasks, empty=False)
        empty_score, empty_passes = _score_tasks(suite.path.parent, tasks, empty=True)
        assert reference_score == 10, reference_failures
        assert empty_score == 0, empty_passes


def _score_tasks(
    suite_dir: Path,
    tasks: list[EvalTask],
    *,
    empty: bool,
) -> tuple[int, list[str]]:
    green: int = 0
    notes: list[str] = []
    for task in tasks:
        with tempfile.TemporaryDirectory(prefix=f"roop-oracle-{task.id}-") as temporary:
            project: Path = _materialize(Path(temporary), suite_dir, task, empty=empty)
            completed: subprocess.CompletedProcess[str] = subprocess.run(
                task.verify_command,
                cwd=project,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
            )
        if completed.returncode == 0:
            green += 1
            if empty:
                notes.append(task.id)
        elif not empty:
            detail: str = (completed.stderr or completed.stdout)[-800:]
            notes.append(f"{task.id}\n{detail}")
    return green, notes


def _materialize(
    project: Path,
    suite_dir: Path,
    task: EvalTask,
    *,
    empty: bool,
) -> Path:
    source_root: Path = REFERENCE_ROOT / task.id / "src"
    assert source_root.is_dir(), f"missing reference for {task.id}"
    destination: Path = project / "src"
    if empty:
        destination.mkdir(parents=True)
        for path in source_root.rglob("*.py"):
            target: Path = destination / path.relative_to(source_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('"""Empty implementation."""\n', encoding="utf-8")
    else:
        shutil.copytree(source_root, destination)
    golden: Path = suite_dir / str(task.golden_test)
    tests_dir: Path = project / "tests"
    tests_dir.mkdir(parents=True)
    shutil.copyfile(golden, tests_dir / golden.name)
    return project
