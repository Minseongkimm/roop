"""Local-loop harness: failure text, module map, syntax check, retry budget."""

from __future__ import annotations

import json
from pathlib import Path

from roop.adapters.model import ModelResponse
from roop.adapters.ollama import TransientOllamaError
from roop.context.builder import ContextBuilder
from roop.context.roles import AgentRole
from roop.executor.agent import ExecutionResult, _messages_from_packet
from roop.harness.tools import CommandResult
from roop.orchestrator.loop import OrchestratorLoop
from roop.orchestrator.tasks import DEFAULT_MAX_RETRIES, TaskStatus, TaskStore
from roop.verifier.engine import Verifier
from roop.verifier.report import compile_sources, summarize_test_failure


def test_default_local_attempts_are_four() -> None:
    assert DEFAULT_MAX_RETRIES == 4


def test_summary_keeps_traceback_and_assertion() -> None:
    noise = "\n".join(f"test_{index} ... FAIL" for index in range(40))
    stderr = (
        noise
        + "\nTraceback (most recent call last):\n"
        + "  File \"tests/test_money_ledger.py\", line 12, in test_parse\n"
        + "    self.assertEqual(parse_cents('1.2'), 120)\n"
        + "AssertionError: 100 != 120\n"
    )
    summary = summarize_test_failure("", stderr)
    assert summary.startswith("Traceback (most recent call last):")
    assert "AssertionError: 100 != 120" in summary
    assert "test_0" not in summary


def test_py_compile_failure_skips_the_test_command(tmp_path: Path) -> None:
    project = tmp_path / "app"
    source = project / "src" / "money.py"
    source.parent.mkdir(parents=True)
    source.write_text("def parse_cents(\n", encoding="utf-8")
    marker = project / "ran.txt"
    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task(
        "money",
        allow_paths="src/**",
        verify_command=f"python3 -c \"open('{marker}', 'w').write('yes')\"",
    )
    execution = ExecutionResult(
        role=AgentRole.CODER,
        task_id=task.id,
        ok=True,
        model_raw="{}",
        parsed={},
        patches=[],
        command=None,
    )
    result = Verifier(project).verify(task, execution)
    assert result.green is False
    assert "SyntaxError" in result.saw
    assert "py_compile" in result.feedback()
    assert marker.exists() is False
    assert "SyntaxError" in compile_sources(project)


def test_verifier_puts_assertion_in_feedback(tmp_path: Path) -> None:
    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    (project / "src" / "clamp.py").write_text(
        "def clamp(value, low, high):\n    return value\n",
        encoding="utf-8",
    )
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_clamp.py").write_text(
        "import unittest\n"
        "from src.clamp import clamp\n"
        "class T(unittest.TestCase):\n"
        "    def test_low(self):\n"
        "        self.assertEqual(clamp(-1, 0, 10), 0)\n",
        encoding="utf-8",
    )
    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task(
        "clamp",
        allow_paths="src/**",
        verify_command="python3 -m unittest discover -s tests -p test_clamp.py -v",
    )
    execution = ExecutionResult(
        role=AgentRole.CODER,
        task_id=task.id,
        ok=True,
        model_raw="{}",
        parsed={},
        patches=[],
    )
    result = Verifier(project).verify(task, execution)
    feedback = result.feedback()
    assert result.green is False
    assert "AssertionError" in feedback
    assert "Traceback" in feedback
    packet = ContextBuilder(project).build(
        task,
        AgentRole.CODER,
        verifier_feedback=feedback,
    )
    assert "AssertionError" in packet.verifier_feedback
    rendered = "\n".join(message.content for message in _messages_from_packet(packet))
    assert "AssertionError" in rendered


def test_module_map_lists_imports_signatures_and_contents(tmp_path: Path) -> None:
    project = tmp_path / "app"
    source = project / "src" / "clamp.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def clamp(value, low, high):\n    return value\n",
        encoding="utf-8",
    )
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_clamp.py").write_text(
        "from src.clamp import clamp\n\n"
        "def test_clamp():\n"
        "    assert clamp(1, 0, 2) == 1\n",
        encoding="utf-8",
    )
    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task(
        "clamp",
        allow_paths="src/**",
        verify_command="python3 -m unittest discover -s tests -p test_clamp.py -v",
    )
    packet = ContextBuilder(project).build(task, AgentRole.CODER)
    assert "from src.clamp import clamp" in packet.module_map
    assert "src/clamp.py" in packet.module_map
    assert "def clamp(value, low, high)" in packet.module_map
    assert "return value" in packet.module_map
    rendered = "\n".join(message.content for message in _messages_from_packet(packet))
    assert "Expected import paths" in rendered
    assert "def clamp(value, low, high)" in rendered


def test_module_map_marks_a_missing_file(tmp_path: Path) -> None:
    project = tmp_path / "app"
    tests = project / "tests"
    tests.mkdir(parents=True)
    (tests / "test_money_ledger.py").write_text(
        "from src.money import parse_cents, format_cents\n"
        "from src.ledger import Ledger\n",
        encoding="utf-8",
    )
    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task(
        "money",
        allow_paths="src/**",
        verify_command="python3 -m unittest discover -s tests -p test_money_ledger.py -v",
    )
    packet = ContextBuilder(project).build(task, AgentRole.CODER)
    assert "src/money.py" in packet.module_map
    assert "MISSING" in packet.module_map
    assert "parse_cents" in packet.module_map
    assert "src/ledger.py" in packet.module_map


def test_transient_ollama_error_does_not_spend_a_retry(tmp_path: Path) -> None:
    class Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages, *, model=None):
            self.calls += 1
            raise TransientOllamaError("HTTP 500")

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["qwen2.5-coder:7b"]

    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    (project / ".agent" / "project").mkdir(parents=True)
    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "retry me",
        feature_ids="eval,easy,demo",
        allow_paths="src/**",
        verify_command="false",
        max_retries=4,
    )
    model = Flaky()
    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        model=model,
    )
    first = loop.tick()
    assert "TRANSIENT" in first.message
    task = store.get_task(1)
    assert task.status == TaskStatus.PENDING
    assert task.retry_count == 0
    assert task.local_verify_failures == 0
    assert task.transient_attempts == 1
    loop.tick()
    loop.tick()
    task = store.get_task(1)
    assert task.status == TaskStatus.BLOCKED
    assert task.retry_count == 0
    assert model.calls == 3


def test_easy_uses_four_local_attempts_and_never_calls_api(tmp_path: Path) -> None:
    class LocalModel:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages, *, model=None):
            self.calls += 1
            body = json.dumps(
                {"files": [{"path": "src/x.py", "content": f"value = {self.calls}\n"}]}
            )
            return ModelResponse(content=body, model="qwen2.5-coder:7b")

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["qwen2.5-coder:7b"]

    class ApiModel:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages, *, model=None):
            self.calls += 1
            return ModelResponse(content="{}", model="gpt-4o-mini", provider="api")

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["gpt-4o-mini"]

    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    (project / ".agent" / "project").mkdir(parents=True)
    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "stay local",
        feature_ids="eval,easy,demo",
        allow_paths="src/**",
        verify_command="false",
        max_retries=4,
    )
    local = LocalModel()
    api = ApiModel()
    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        model=local,
        api_model=api,
    )
    messages = [loop.tick().message for _ in range(4)]
    assert all("API_SKIPPED" not in message for message in messages)
    assert local.calls == 4
    assert api.calls == 0
    task = store.get_task(1)
    assert task.status == TaskStatus.BLOCKED
    assert task.retry_count == 4
    assert task.outcome == "fail"
    assert "Assertion" not in task.last_failure_feedback or "false" in task.last_failure_feedback


def test_failed_attempt_feedback_includes_tested_source(tmp_path: Path) -> None:
    class LocalModel:
        def chat(self, messages, *, model=None):
            return ModelResponse(
                content=json.dumps(
                    {
                        "files": [
                            {
                                "path": "src/clamp.py",
                                "content": "def clamp(value, low, high):\n    return value\n",
                            }
                        ]
                    }
                ),
                model="qwen2.5-coder:7b",
            )

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["local"]

    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    (project / ".agent" / "project").mkdir(parents=True)
    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "clamp",
        feature_ids="eval,easy,clamp",
        allow_paths="src/**",
        verify_command="false",
        max_retries=4,
    )
    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        model=LocalModel(),
    )
    loop.tick()
    feedback = store.get_task(1).last_failure_feedback
    assert "def clamp(value, low, high)" in feedback
    assert "src that was tested" in feedback
    assert (project / "src" / "clamp.py").exists() is False


def test_command_result_summary_is_used_when_already_run(tmp_path: Path) -> None:
    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task("ran", allow_paths="src/**", verify_command="false")
    execution = ExecutionResult(
        role=AgentRole.CODER,
        task_id=task.id,
        ok=True,
        model_raw="{}",
        parsed={},
        patches=[],
        command=CommandResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="Traceback (most recent call last):\nAssertionError: left != right\n",
        ),
    )
    result = Verifier(project).verify(task, execution, run_command=False)
    assert "AssertionError: left != right" in result.saw
