"""Failure-aware retry loop: classify, change the prompt, escalate, keep tests locked."""

from __future__ import annotations

from pathlib import Path

from roop.engines.base import EngineGeneration, EngineRequest
from roop.engines.escalation import build_escalation_engine, escalation_config
from roop.engines.retry_loop import (
    build_retry_prompt,
    classify_test_failure,
    failing_tests,
    run_retry_loop,
)
from roop.eval.retry_eval import summarize

TEST_CMD = "python3 -m unittest discover -s tests -p test_add.py -v"
GOOD = "def add(a, b):\n    return a + b\n"
WRONG = "def add(a, b):\n    return a - b\n"
TEST_BODY = (
    "import sys, unittest\n"
    "sys.path.insert(0, 'src')\n"
    "from adder import add\n"
    "class T(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(add(2, 3), 5)\n"
)


class ScriptedEngine:
    def __init__(self, outputs: list[str | None], name: str = "local") -> None:
        self.outputs = list(outputs)
        self.prompts: list[str] = []
        self.seen_files: list[str] = []
        self.name = name

    def generate(self, request: EngineRequest) -> EngineGeneration:
        self.prompts.append(request.prompt)
        target = request.workdir / "src" / "adder.py"
        self.seen_files.append(target.read_text() if target.exists() else "")
        body = self.outputs.pop(0) if self.outputs else WRONG
        if body is None:
            return EngineGeneration(format_ok=False, format_error="no edit")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        return EngineGeneration(format_ok=True)


def _project(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_add.py").write_text(TEST_BODY)
    return tmp_path


def _run(tmp_path: Path, engine, **kwargs):  # type: ignore[no-untyped-def]
    return run_retry_loop(
        engine,
        prompt="SPEC: create src/adder.py with add(a, b).",
        editable_files=("src/adder.py",),
        test_command=TEST_CMD,
        workdir=_project(tmp_path),
        **kwargs,
    )


def test_classify_common_unittest_failures() -> None:
    assert classify_test_failure("  File x\nSyntaxError: invalid syntax") == "syntax"
    assert classify_test_failure("ModuleNotFoundError: No module named 'adder'") == "import"
    assert classify_test_failure("ImportError: cannot import name 'add'") == "import"
    assert classify_test_failure("FAIL: test_a (t.T)\nAssertionError: 1 != 5") == "assertion"
    assert classify_test_failure("FAIL: test_a (t.T)\nAssertionError: ValueError not raised") == "exception"
    assert classify_test_failure("ERROR: test_a (t.T)\nTraceback\nTypeError: bad operand") == "exception"
    assert classify_test_failure("", timed_out=True) == "timeout"
    out = "FAIL: test_b (t.T.test_b)\nERROR: test_a (t.T.test_a)\n"
    assert failing_tests(out) == ("test_a", "test_b")


def test_first_pass_counts_once(tmp_path: Path) -> None:
    engine = ScriptedEngine([GOOD])
    result = _run(tmp_path, engine)
    assert result.first_pass and result.local_eventual and result.eventual
    assert result.attempts_used == 1
    assert engine.prompts[0].startswith("SPEC:")


def test_retry_prompt_has_spec_failure_and_log(tmp_path: Path) -> None:
    engine = ScriptedEngine([WRONG, GOOD])
    result = _run(tmp_path, engine)
    assert not result.first_pass
    assert result.local_eventual and result.eventual and not result.escalated
    assert result.attempts_used == 2
    assert result.kinds == ("assertion",)
    retry = engine.prompts[1]
    assert "SPEC: create src/adder.py" in retry
    assert "attempt 1" in retry and "failure=assertion" in retry and "test_add" in retry
    assert "5 != -1" in retry or "-1 != 5" in retry
    # repair mode: the previous attempt stays in the file
    assert engine.seen_files[1] == WRONG


def test_same_failure_twice_resets_and_asks_for_new_approach(tmp_path: Path) -> None:
    engine = ScriptedEngine([WRONG, WRONG, GOOD])
    result = _run(tmp_path, engine)
    assert result.attempts_used == 3 and result.local_eventual
    assert "different implementation strategy" in engine.prompts[2]
    assert engine.seen_files[2] == ""  # fresh tree, previous code discarded
    assert result.attempts[2].fresh_start


def test_three_local_failures_without_escalation(tmp_path: Path) -> None:
    result = _run(tmp_path, ScriptedEngine([WRONG, None, WRONG]))
    assert not result.eventual and not result.escalated
    assert result.local_attempts == 3
    assert "format" in result.kinds


def test_test_edits_are_reverted_and_cannot_pass(tmp_path: Path) -> None:
    class Cheater(ScriptedEngine):
        def generate(self, request: EngineRequest) -> EngineGeneration:
            (request.workdir / "tests" / "test_add.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_add(self):\n        pass\n"
            )
            return super().generate(request)

    result = _run(tmp_path, Cheater([WRONG]), max_local_attempts=1)
    assert not result.eventual
    assert result.attempts[0].locked_reverted == ("tests/test_add.py",)
    assert (tmp_path / "tests" / "test_add.py").read_text() == TEST_BODY


def test_escalation_after_local_budget(tmp_path: Path) -> None:
    api = ScriptedEngine([GOOD], name="api:test")
    result = _run(tmp_path, ScriptedEngine([WRONG, WRONG, WRONG]), escalation_engine=api)
    assert not result.first_pass and not result.local_eventual
    assert result.escalated and result.escalation_solved and result.eventual
    assert result.local_attempts == 3 and result.attempts_used == 4
    assert result.attempts[-1].engine == "api:test"
    assert "smaller model could not solve" in api.prompts[0]


def test_escalation_not_used_when_local_passes(tmp_path: Path) -> None:
    api = ScriptedEngine([GOOD], name="api:test")
    result = _run(tmp_path, ScriptedEngine([GOOD]), escalation_engine=api)
    assert not result.escalated and api.prompts == []


def test_escalation_config_default_disabled_and_key_by_name(tmp_path: Path) -> None:
    assert escalation_config(environ={}).problem() == "disabled"
    config = escalation_config(preset="groq", environ={})
    assert config.enabled and config.key_env == "GROQ_API_KEY"
    assert "api.groq.com" in config.base_url
    missing = escalation_config(enabled=True, base_url="http://x/v1", model="m", key_env="ROOP_TEST_NO_SUCH_KEY", environ={})
    assert missing.problem() == "env ROOP_TEST_NO_SUCH_KEY is empty"
    assert build_escalation_engine(missing) is None


def test_escalation_engine_passes_key_only_via_env(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ROOP_TEST_KEY", "secret-value-123")
    seen: dict[str, object] = {}

    def runner(command, **kwargs):  # type: ignore[no-untyped-def]
        import subprocess

        seen["command"] = command
        seen["env"] = kwargs["env"]
        (kwargs["cwd"] / "src" / "adder.py").write_text(GOOD)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    config = escalation_config(enabled=True, base_url="http://x/v1", model="m1", key_env="ROOP_TEST_KEY", environ={})
    engine = build_escalation_engine(config, binary="aider", runner=runner)
    assert engine is not None
    workdir = _project(tmp_path)
    engine.generate(EngineRequest(prompt="p", editable_files=("src/adder.py",), test_command=TEST_CMD, workdir=workdir))
    assert "secret-value-123" not in " ".join(seen["command"])  # type: ignore[arg-type]
    assert seen["env"]["OPENAI_API_KEY"] == "secret-value-123"  # type: ignore[index]
    assert seen["env"]["OPENAI_API_BASE"] == "http://x/v1"  # type: ignore[index]
    assert seen["command"][seen["command"].index("--model") + 1] == "openai/m1"  # type: ignore[union-attr,index]
    settings = (workdir / ".agent" / "aider-model.yml").read_text()
    assert "secret" not in settings and "num_ctx" not in settings and "max_tokens" in settings


def test_summary_separates_local_and_api() -> None:
    rows = [
        {"first_pass": True, "local_eventual": True, "eventual": True, "local_attempts": 1},
        {"first_pass": False, "local_eventual": True, "eventual": True, "local_attempts": 2},
        {"first_pass": False, "local_eventual": False, "eventual": True, "escalated": True, "escalation_solved": True, "local_attempts": 3},
        {"first_pass": False, "local_eventual": False, "eventual": False, "escalated": True, "local_attempts": 3},
    ]
    line = summarize(rows)
    assert "first-pass 1/4 (25%)" in line
    assert "local eventual 2/4 (50%)" in line
    assert "eventual incl. API 3/4 (75%)" in line
    assert "escalated 2 solved 1" in line


def test_build_retry_prompt_first_attempt_is_plain_spec() -> None:
    assert build_retry_prompt("SPEC", [], fresh_start=False) == "SPEC"
