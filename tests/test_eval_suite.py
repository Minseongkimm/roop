"""Tests for eval suite loading and tamper detection."""

from __future__ import annotations

from pathlib import Path

from roop.eval.runner import enqueue_suite, run_suite
from roop.eval.suite import default_suite_path, load_suite
from roop.eval.tamper import TamperGuard
from roop.orchestrator.tasks import TaskStore


def test_load_default_suite() -> None:
    suite = load_suite(default_suite_path())
    assert suite.name == "roop-eval-v1"
    assert len(suite.tasks) >= 5
    assert suite.by_difficulty("easy")


def test_enqueue_suite(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    db = project / ".agent" / "roop-eval.sqlite3"
    suite = load_suite(default_suite_path())
    result = enqueue_suite(
        project_root=project,
        suite=suite,
        database_path=db,
        task_ids=["clamp-util"],
    )
    assert len(result.task_ids) == 1
    store = TaskStore(db)
    task = store.get_task(result.task_ids[0])
    assert "clamp" in task.title.lower()
    assert task.allow_paths == "src/**"
    assert (project / "tests" / "test_clamp.py").is_file()


def test_noop_verify_command_rejected() -> None:
    from roop.eval.suite import is_noop_verify_command

    assert is_noop_verify_command("") is True
    assert is_noop_verify_command("true") is True
    assert is_noop_verify_command(":") is True
    assert is_noop_verify_command("python3 -m unittest discover -s tests -v") is False


def test_tamper_guard_detects_modified_test(tmp_path: Path) -> None:
    project = tmp_path / "app"
    tests = project / "tests"
    tests.mkdir(parents=True)
    target = tests / "test_clamp.py"
    target.write_text("assert True\n", encoding="utf-8")
    guard = TamperGuard(project, ("tests/test_clamp.py",))
    guard.snapshot()
    target.write_text("assert False\n", encoding="utf-8")
    result = guard.check()
    assert result.ok is False
    assert "tests/test_clamp.py" in result.changed_paths


def test_run_suite_dry_run_enqueue_only_execute(tmp_path: Path) -> None:
    project = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("x\n", encoding="utf-8")
    (project / "src").mkdir()
    (project / "tests").mkdir()
    db = project / ".agent" / "roop-eval.sqlite3"
    result = run_suite(
        project_root=project,
        suite_path=default_suite_path(),
        database_path=db,
        task_ids=["clamp-util"],
        execute=True,
        dry_run=True,
        max_ticks=3,
    )
    assert len(result.enqueued.task_ids) == 1
    assert any(item.did_work for item in result.tick_results)
