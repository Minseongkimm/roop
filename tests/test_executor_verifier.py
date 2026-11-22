"""Tests for Phase 4–6 executor, verifier, night scheduler."""

from __future__ import annotations

from pathlib import Path

from roop.context.roles import AgentRole
from roop.executor.agent import AgentExecutor, ExecutionResult
from roop.executor.json_util import parse_json_object
from roop.harness.fs_guard import WriteGuard
from roop.memory.lessons import Lesson, LessonStore
from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import Task, TaskStatus, TaskStore
from roop.scheduler.night import NightRunResult, NightScheduler, write_launchd_plist
from roop.verifier.engine import Verifier, VerifyResult


def test_parse_json_object_from_fence() -> None:
    # Arrange
    raw: str = 'Sure.\n```json\n{"approved": true, "blocking_issues": []}\n```\n'
    # Act
    actual: dict[str, object] = parse_json_object(raw)
    # Assert
    assert actual["approved"] is True


def test_dry_run_coder_tick_is_green(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("demo\n", encoding="utf-8")
    db: Path = project / ".agent" / "tasks.sqlite3"
    store: TaskStore = TaskStore(db)
    store.create_task(
        "dry coder",
        allow_paths=".agent/**",
        verify_command="true",
        max_retries=3,
    )
    loop: OrchestratorLoop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        dry_run=True,
    )
    # Act
    result: TickResult = loop.tick()
    # Assert
    assert result.did_work is True
    assert result.green is True
    assert (project / ".agent" / "scratch" / "dry-run.txt").is_file()
    assert (project / ".agent" / "memory" / "lessons.md").is_file()
    assert store.get_task(1).status == TaskStatus.DONE


def test_verifier_rejects_failed_patch(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    project.mkdir()
    store: TaskStore = TaskStore(project / ".agent" / "t.sqlite3")
    task: Task = store.create_task("x", allow_paths=".agent/**")
    execution: ExecutionResult = ExecutionResult(
        role=AgentRole.CODER,
        task_id=task.id,
        ok=False,
        model_raw="{}",
        parsed={},
        patches=[],
        message="no patches",
    )
    # Act
    actual: VerifyResult = Verifier(project).verify(task, execution)
    # Assert
    assert actual.green is False


def test_allow_paths_guard(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    project.mkdir()
    (project / "src").mkdir()
    guard: WriteGuard = WriteGuard(project).with_allow_paths("src/**")
    # Act
    written: Path = guard.write_text("src/ok.txt", "hi")
    # Assert
    assert written.read_text(encoding="utf-8") == "hi"
    assert guard.is_write_allowed(Path("README.md")) is False


def test_night_scheduler_dry_run(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("x\n", encoding="utf-8")
    db: Path = project / ".agent" / "roop-tasks.sqlite3"
    store: TaskStore = TaskStore(db)
    store.create_task("night one", allow_paths=".agent/**", verify_command="true")
    scheduler: NightScheduler = NightScheduler(
        project,
        db,
        role=AgentRole.CODER,
        dry_run=True,
        max_ticks=5,
    )
    # Act
    result: NightRunResult = scheduler.run()
    # Assert
    assert result.green >= 1
    assert result.report_path is not None
    assert result.report_path.is_file()
    assert (project / ".agent" / "reports" / "latest.md").is_file()


def test_write_launchd_plist(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    project.mkdir()
    # Act
    path: Path = write_launchd_plist(project_root=project, hour=3, dry_run=True)
    # Assert
    assert path.is_file()
    text: str = path.read_text(encoding="utf-8")
    assert "com.roop.night" in text
    assert "--dry-run" in text
    assert (project / ".agent" / "scheduler" / "README.md").is_file()


def test_lesson_store_append(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    project.mkdir()
    store: LessonStore = LessonStore(project)
    # Act
    path: Path = store.append(
        Lesson(task_id=1, summary="fixed redirect", evidence="exit 0")
    )
    # Assert
    assert "fixed redirect" in path.read_text(encoding="utf-8")


def test_executor_dry_run_planner_enqueues(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("o\n", encoding="utf-8")
    db: Path = project / ".agent" / "t.sqlite3"
    store: TaskStore = TaskStore(db)
    task: Task = store.create_task("goal")
    executor: AgentExecutor = AgentExecutor(project, store, dry_run=True)
    # Act
    result: ExecutionResult = executor.execute(task, AgentRole.PLANNER)
    # Assert
    assert result.ok is True
    assert len(result.enqueued_task_ids) == 1
