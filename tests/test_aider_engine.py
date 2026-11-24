"""Aider is an adapter: whole-file edits, no auto-commit, harness still grades."""

from __future__ import annotations

import subprocess
from pathlib import Path

from roop.engines.aider_engine import (
    AIDER_MODEL,
    AiderEngine,
    build_aider_command,
    model_settings_text,
)
from roop.engines.budget import (
    MAX_SECONDS_PER_GENERATION,
    MAX_SECONDS_PER_MULTIFILE_GENERATION,
)
from roop.engines.base import EngineRequest
from roop.eval.compare import run_compare
from roop.eval.suite import load_suite


def test_aider_command_adds_every_src_file_and_disables_commits() -> None:
    request = EngineRequest(
        prompt="implement both files",
        editable_files=("src/left.py", "src/right.py"),
        test_command="python3 -m unittest discover -s tests -p test_left.py -v",
        workdir=Path("/tmp/work"),
        temperature=0.4,
    )
    command = build_aider_command(
        request,
        binary="aider",
        model=AIDER_MODEL,
        settings_path=Path("/tmp/work/.agent/aider-model.yml"),
    )
    assert command[command.index("--edit-format") + 1] == "whole"
    assert "--no-auto-commits" in command
    assert "--no-git" in command
    assert "--no-auto-test" in command
    assert "--yes-always" in command
    assert "--no-pretty" in command
    assert "--no-stream" in command
    assert "--no-check-update" in command
    assert "--no-show-model-warnings" in command
    assert command[command.index("--model") + 1] == "ollama_chat/qwen2.5-coder:7b"
    assert command[command.index("--test-cmd") + 1] == request.test_command
    assert command[command.index("--message") + 1] == request.prompt
    assert command[-2:] == ["src/left.py", "src/right.py"]
    settings = model_settings_text(
        model=AIDER_MODEL,
        temperature=0.4,
        num_ctx=8192,
    )
    assert "use_temperature: 0.4" in settings
    assert "num_ctx: 8192" in settings
    assert "edit_format: whole" in settings


def test_aider_generate_creates_missing_files_and_reports_an_edit(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["command"] = command
        seen["cwd"] = kwargs["cwd"]
        workdir: Path = kwargs["cwd"]  # type: ignore[assignment]
        (workdir / "src" / "right.py").write_text("changed\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="edited", stderr="")

    engine = AiderEngine(binary="aider-bin", runner=runner)
    generation = engine.generate(
        EngineRequest(
            prompt="edit both",
            editable_files=("src/left.py", "src/right.py"),
            test_command="python3 -m unittest discover -s tests -v",
            workdir=tmp_path,
            temperature=0.2,
        )
    )
    command = seen["command"]
    assert isinstance(command, list)
    assert "src/left.py" in command and "src/right.py" in command
    assert (tmp_path / "src" / "left.py").is_file()
    assert generation.format_ok is True
    settings = (tmp_path / ".agent" / "aider-model.yml").read_text(encoding="utf-8")
    assert "use_temperature: 0.2" in settings
    assert "num_ctx: 8192" in settings


def test_identical_applied_edit_is_unchanged_not_a_banner(tmp_path: Path) -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="Detected dumb terminal, disabling fancy input.\nApplied edit to left.py\n",
            stderr="",
        )

    generation = AiderEngine(binary="aider", runner=runner).generate(
        EngineRequest(
            prompt="edit",
            editable_files=("src/left.py",),
            test_command="python3 -m unittest discover -s tests -v",
            workdir=tmp_path,
        )
    )
    assert generation.format_ok is False
    assert generation.format_error == "unchanged"


def test_multifile_generation_timeout_is_longer(tmp_path: Path) -> None:
    seen: dict[str, float] = {}

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["timeout"] = float(kwargs["timeout"])  # type: ignore[arg-type]
        workdir: Path = kwargs["cwd"]  # type: ignore[assignment]
        (workdir / "src" / "right.py").write_text("changed\n", encoding="utf-8")
        (workdir / "src" / "only.py").write_text("changed\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="edited", stderr="")

    engine = AiderEngine(binary="aider", runner=runner)
    engine.generate(
        EngineRequest(
            prompt="edit both",
            editable_files=("src/left.py", "src/right.py"),
            test_command="python3 -m unittest discover -s tests -v",
            workdir=tmp_path,
        )
    )
    assert MAX_SECONDS_PER_MULTIFILE_GENERATION == 600.0
    assert seen["timeout"] == 600.0
    engine.generate(
        EngineRequest(
            prompt="edit one",
            editable_files=("src/only.py",),
            test_command="python3 -m unittest discover -s tests -v",
            workdir=tmp_path / "one",
        )
    )
    assert seen["timeout"] == MAX_SECONDS_PER_GENERATION


def test_compare_keeps_pass_rates_for_a_fake_engine(tmp_path: Path) -> None:
    golden = tmp_path / "golden" / "tests"
    golden.mkdir(parents=True)
    (golden / "test_ok.py").write_text("print('unused')\n", encoding="utf-8")
    manifest = tmp_path / "suite.json"
    manifest.write_text(
        """
        {
          "name": "tiny",
          "tasks": [
            {
              "id": "ok-task",
              "title": "Ok",
              "difficulty": "easy",
              "split": "heldout",
              "description": "Write src/ok.py",
              "verify_command": "python3 -c \\"import pathlib; assert pathlib.Path('src/ok.py').read_text()=='ok\\\\n'\\"",
              "golden_test": "golden/tests/test_ok.py",
              "src_files": ["src/ok.py"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    class _Engine:
        name = "fake"

        def generate(self, request: EngineRequest) -> object:
            path = request.workdir / "src" / "ok.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ok\n", encoding="utf-8")
            from roop.engines.base import EngineGeneration

            return EngineGeneration(format_ok=True, raw_output="ok")

    results = run_compare(
        engine=_Engine(),
        suite=load_suite(manifest),
        workspace=tmp_path / "run",
        split="heldout",
        difficulty="easy",
    )
    assert len(results) == 1
    assert results[0].passed_at_1 is True
    assert results[0].passed_best is True
    assert (tmp_path / "run" / "scorecard.txt").is_file()
