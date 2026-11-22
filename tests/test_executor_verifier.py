"""Tests for Phase 4–6 executor, verifier, night scheduler."""

from __future__ import annotations

from pathlib import Path

from roop.adapters.model import ModelResponse

from roop.context.roles import AgentRole
from roop.executor.agent import AgentExecutor, ExecutionResult
from roop.executor.json_util import parse_json_object
from roop.harness.fs_guard import WriteGuard
from roop.harness.tools import FileTransaction, ToolHarness
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

def test_file_transaction_rolls_back_existing_file(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    target = project / "existing.txt"
    target.write_bytes(b"original\\r\\n")

    transaction = FileTransaction(project)
    transaction.capture("existing.txt")
    target.write_text("modified", encoding="utf-8")
    transaction.rollback()

    assert target.read_bytes() == b"original\\r\\n"


def test_file_transaction_removes_new_file_on_rollback(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    transaction = FileTransaction(project)
    transaction.capture("new/file.txt")

    target = project / "new" / "file.txt"
    target.parent.mkdir()
    target.write_text("new content", encoding="utf-8")
    transaction.rollback()

    assert not target.exists()


def test_file_transaction_commit_keeps_changes(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    target = project / "existing.txt"
    target.write_text("original", encoding="utf-8")

    transaction = FileTransaction(project)
    transaction.capture("existing.txt")
    target.write_text("committed", encoding="utf-8")
    transaction.commit()
    transaction.rollback()

    assert target.read_text(encoding="utf-8") == "committed"

def test_orchestrator_rolls_back_file_when_verification_fails(tmp_path: Path) -> None:
    class FakeModel:
        def chat(self, messages, *, model=None):
            return ModelResponse(
                content='{"files":[{"path":"src/example.py","find":"original","replace":"changed"}]}',
                model="fake",
            )

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["fake"]

    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    target = project / "src" / "example.py"
    target.write_text("original", encoding="utf-8")

    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "change example",
        allow_paths="src/**",
        verify_command="false",
        max_retries=3,
    )

    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        model=FakeModel(),
    )

    result = loop.tick()

    assert result.did_work is True
    assert result.green is False
    assert target.read_text(encoding="utf-8") == "original"


def test_patch_requires_exactly_one_match(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    target = project / "example.py"
    target.write_text("before\nvalue = 1\nafter\n", encoding="utf-8")
    harness = ToolHarness(
        project,
        WriteGuard(project).with_allow_paths("**"),
    )

    result = harness.apply_unified_hunk(
        "example.py",
        find="value = 1",
        replace="value = 2",
    )

    assert result.applied is True
    assert target.read_text(encoding="utf-8") == "before\nvalue = 2\nafter\n"


def test_patch_rejects_missing_match(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    target = project / "example.py"
    target.write_text("value = 1\n", encoding="utf-8")
    harness = ToolHarness(
        project,
        WriteGuard(project).with_allow_paths("**"),
    )

    result = harness.apply_unified_hunk(
        "example.py",
        find="value = 9",
        replace="value = 2",
    )

    assert result.applied is False
    assert target.read_text(encoding="utf-8") == "value = 1\n"


def test_patch_rejects_ambiguous_match(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    target = project / "example.py"
    target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    harness = ToolHarness(
        project,
        WriteGuard(project).with_allow_paths("**"),
    )

    result = harness.apply_unified_hunk(
        "example.py",
        find="value = 1",
        replace="value = 2",
    )

    assert result.applied is False
    assert "ambiguous" in result.detail
    assert target.read_text(encoding="utf-8") == "value = 1\nvalue = 1\n"


def test_executor_rejects_full_content_for_existing_file(tmp_path: Path) -> None:
    class FakeModel:
        def chat(self, messages, *, model=None):
            return ModelResponse(
                content='{"files":[{"path":"src/example.py","content":"destroyed"}]}',
                model="fake",
            )

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["fake"]

    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    target = project / "src" / "example.py"
    target.write_text("original\n", encoding="utf-8")

    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task(
        "reject overwrite",
        allow_paths="src/**",
        verify_command="true",
    )
    executor = AgentExecutor(project, store, model=FakeModel())

    result = executor.execute(task, AgentRole.CODER)

    assert result.ok is False
    assert len(result.patches) == 1
    assert result.patches[0].applied is False
    assert "full-file overwrite" in result.patches[0].detail
    assert target.read_text(encoding="utf-8") == "original\n"
