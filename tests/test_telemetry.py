"""Tests for round JSONL telemetry and night hard-stop."""

from __future__ import annotations

import json
from pathlib import Path

from roop.context.roles import AgentRole
from roop.orchestrator.loop import OrchestratorLoop
from roop.orchestrator.tasks import TaskStore
from roop.scheduler.night import NightScheduler
from roop.telemetry.rounds import RoundLog, RoundRecord, extract_test_counts, utc_now_iso
from roop.telemetry.wip import commit_wip_branch


def test_extract_test_counts_ok() -> None:
    output = "test_mean ... ok\n\n----------------------------------------------------------------------\nRan 2 tests in 0.000s\n\nOK\n"
    ran, passed = extract_test_counts(output)
    assert ran == 2
    assert passed == 2


def test_extract_test_counts_zero() -> None:
    output = "----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n"
    ran, passed = extract_test_counts(output)
    assert ran == 0
    assert passed == 0


def test_round_log_append(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    log = RoundLog(project)
    path = log.append(
        RoundRecord(
            ts=utc_now_iso(),
            task_id=1,
            role="coder",
            green=True,
            exit_code=0,
            error_signature="",
            tests_ran=2,
            tests_passed=2,
            tokens_est=40,
            model="dry-run",
            message="ok",
            status="done",
        )
    )
    assert path.is_file()
    rows = log.read_all()
    assert len(rows) == 1
    assert rows[0]["task_id"] == 1
    assert rows[0]["green"] is True


def test_dry_run_tick_writes_rounds_jsonl(tmp_path: Path) -> None:
    project = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("demo\n", encoding="utf-8")
    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "dry coder",
        allow_paths=".agent/**",
        verify_command="true",
        max_retries=3,
    )
    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        dry_run=True,
    )
    result = loop.tick()
    assert result.green is True
    rounds = project / ".agent" / "runs" / "rounds.jsonl"
    assert rounds.is_file()
    row = json.loads(rounds.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["green"] is True
    assert row["task_id"] == 1


def test_night_max_ticks_sets_stop_reason(tmp_path: Path) -> None:
    project = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("x\n", encoding="utf-8")
    db = project / ".agent" / "roop-tasks.sqlite3"
    store = TaskStore(db)
    store.create_task("one", allow_paths=".agent/**", verify_command="true")
    store.create_task("two", allow_paths=".agent/**", verify_command="true")
    scheduler = NightScheduler(
        project,
        db,
        role=AgentRole.CODER,
        dry_run=True,
        max_ticks=1,
    )
    result = scheduler.run()
    assert result.ticks == 1
    assert result.stop_reason == "max_ticks:1"
    assert (project / ".agent" / "reports" / "latest.md").is_file()
    report = (project / ".agent" / "reports" / "latest.md").read_text(encoding="utf-8")
    assert "Stop reason" in report


def test_commit_wip_branch_when_dirty(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, ["init"])
    _git(project, ["config", "user.email", "roop@test"])
    _git(project, ["config", "user.name", "roop"])
    (project / "README.md").write_text("hi\n", encoding="utf-8")
    _git(project, ["add", "README.md"])
    _git(project, ["commit", "-m", "init"])
    (project / "scratch.txt").write_text("dirty\n", encoding="utf-8")
    branch = commit_wip_branch(project, reason="max_ticks:1")
    assert branch is not None
    assert branch.startswith("wip/roop-")


def _git(cwd: Path, args: list[str]) -> None:
    import subprocess

    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
