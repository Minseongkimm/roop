"""Tests for Phase 3 Context Builder."""

from __future__ import annotations

import json
from pathlib import Path

from roop.context.builder import BuildResult, ContextBuilder, ContextPacket
from roop.context.budget import estimate_tokens, truncate_to_tokens
from roop.context.roles import AgentRole
from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import Task, TaskStore


def test_estimate_and_truncate_tokens() -> None:
    # Arrange
    input_text: str = "abcd" * 100
    # Act
    estimated: int = estimate_tokens(input_text)
    truncated: str = truncate_to_tokens(input_text, max_tokens=10)
    # Assert
    assert estimated == 100
    assert estimate_tokens(truncated) <= 10
    assert "truncated" in truncated


def test_build_packet_uses_agent_docs_and_budget(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    agent: Path = project / ".agent"
    (agent / "project").mkdir(parents=True)
    (agent / "project" / "conventions.md").write_text(
        "# Conventions\n\n- Prefer short answers\n",
        encoding="utf-8",
    )
    (agent / "features" / "chat").mkdir(parents=True)
    (agent / "features" / "chat" / "context.md").write_text(
        "Chat feature handles free messages.\n",
        encoding="utf-8",
    )
    store: TaskStore = TaskStore(agent / "tasks.sqlite3")
    task: Task = store.create_task(
        "chat free message",
        feature_ids="chat",
        acceptance_criteria="free message gate works",
        allow_paths="src/utils/payments/**",
    )
    builder: ContextBuilder = ContextBuilder(project, token_budget=2000)
    # Act
    packet: ContextPacket = builder.build(
        task,
        AgentRole.PLANNER,
        include_code_slices=False,
    )
    # Assert
    assert packet.role == AgentRole.PLANNER
    assert packet.task["id"] == task.id
    assert "Prefer short answers" in packet.project_rules
    assert "Chat feature" in packet.feature_context
    assert packet.estimated_tokens <= packet.token_budget
    assert packet.code_slices == []


def test_build_and_write_creates_packet_files(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text(
        "# Overview\n\nDemo app\n",
        encoding="utf-8",
    )
    store: TaskStore = TaskStore(project / ".agent" / "tasks.sqlite3")
    task: Task = store.create_task("write packet")
    builder: ContextBuilder = ContextBuilder(project)
    # Act
    result: BuildResult = builder.build_and_write(task, AgentRole.CODER)
    # Assert
    assert result.json_path is not None
    assert result.markdown_path is not None
    assert result.json_path.is_file()
    assert result.markdown_path.is_file()
    payload: dict[str, object] = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["role"] == "coder"
    assert payload["task_id"] == task.id


def test_tick_writes_context_packet(tmp_path: Path) -> None:
    # Arrange
    project: Path = tmp_path / "app"
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text(
        "hello\n",
        encoding="utf-8",
    )
    db: Path = project / ".agent" / "tasks.sqlite3"
    store: TaskStore = TaskStore(db)
    store.create_task("packet tick", feature_ids="chat")
    loop: OrchestratorLoop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=False,
    )
    # Act
    result: TickResult = loop.tick()
    # Assert
    assert result.did_work is True
    assert result.packet_path is not None
    assert Path(result.packet_path).is_file()
    assert "Coder" in Path(result.packet_path).read_text(encoding="utf-8") or (
        "coder" in Path(result.packet_path).read_text(encoding="utf-8").lower()
    )

def test_code_slices_include_explicit_allowed_files(tmp_path: Path) -> None:
    project = tmp_path / "app"
    source = project / "src" / "roop" / "tasks.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "class TaskStore:\n    def create_task(self):\n        pass\n",
        encoding="utf-8",
    )

    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task(
        "부모-자식 관계 지원",
        description="SQLite Task 저장소에 parent_task_id를 추가한다.",
        allow_paths="src/roop/tasks.py",
    )

    packet = ContextBuilder(project).build(task, AgentRole.CODER)

    assert any(item.path == "src/roop/tasks.py" for item in packet.code_slices)
    assert any("TaskStore" in item.content for item in packet.code_slices)
def test_rg_files_searches_multiple_terms_with_or(tmp_path: Path) -> None:
    from roop.context.builder import _rg_files

    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    third = tmp_path / "third.py"

    first.write_text("class TaskStore:\n    pass\n", encoding="utf-8")
    second.write_text("parent_task_id = None\n", encoding="utf-8")
    third.write_text("unrelated = True\n", encoding="utf-8")

    results = _rg_files(
        project_root=tmp_path,
        query="TaskStore|parent_task_id",
        limit=3,
    )

    result_names = {path.name for path in results}

    assert result_names == {"first.py", "second.py"}

def test_code_slices_expand_allow_path_globs(tmp_path: Path) -> None:
    project = tmp_path / "app"
    for relative in ("src/core.py", "src/utils/helper.py", "tests/test_core.py"):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative}\nvalue = 1\n", encoding="utf-8")

    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task("glob", allow_paths="src/**,tests/**")
    packet = ContextBuilder(project).build(task, AgentRole.CODER)

    assert {item.path for item in packet.code_slices} == {
        "src/core.py",
        "src/utils/helper.py",
        "tests/test_core.py",
    }


def test_code_slices_glob_excludes_generated_directories(tmp_path: Path) -> None:
    project = tmp_path / "app"
    for relative in (
        "src/real.py",
        ".venv/lib/secret.py",
        ".agent/internal.py",
        "node_modules/pkg/index.py",
        "src/__pycache__/cached.py",
        "build/output.py",
        "coverage/report.py",
    ):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")

    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task("glob", allow_paths="**/*.py")
    packet = ContextBuilder(project).build(task, AgentRole.CODER)
    paths = {item.path for item in packet.code_slices}

    assert "src/real.py" in paths
    assert not any(
        part in {".venv", ".agent", "node_modules", "__pycache__", "build", "coverage"}
        for path in paths
        for part in Path(path).parts[:-1]
    )


def test_code_slices_glob_respects_max_slices(tmp_path: Path) -> None:
    from roop.context import builder as builder_module

    project = tmp_path / "app"
    source = project / "src"
    source.mkdir(parents=True)
    for index in range(10):
        (source / f"module_{index}.py").write_text(
            f"value_{index} = {index}\n",
            encoding="utf-8",
        )

    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task("glob", allow_paths="src/**")
    packet = ContextBuilder(project).build(task, AgentRole.CODER)

    assert builder_module.MAX_SLICES == 8
    assert len(packet.code_slices) == 8
