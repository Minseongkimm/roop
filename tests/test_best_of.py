"""Best-of-5 stays inside its generation cap and the harness grades samples."""

from __future__ import annotations

from pathlib import Path

from roop.adapters.model import ChatMessage, ModelResponse
from roop.engines.base import EngineGeneration, EngineRequest
from roop.engines.budget import (
    BEST_OF_N,
    BEST_OF_TEMPERATURES,
    MAX_GENERATIONS_PER_TASK,
    MAX_SECONDS_PER_GENERATION,
    MAX_SECONDS_PER_TASK,
)
from roop.engines.harness import run_best_of
from roop.engines.roop_engine import RoopEngine
from roop.eval.best_score import (
    BestOfTaskResult,
    aggregate_best_of,
    render_best_of_scorecard,
    top_failure_reasons,
)
from roop.orchestrator.tasks import DEFAULT_MAX_RETRIES


class _ScriptedEngine:
    name: str = "fake"

    def __init__(self, writes: list[dict[str, str]], *, fail_format: bool = False) -> None:
        self._writes: list[dict[str, str]] = writes
        self._fail_format: bool = fail_format
        self.temperatures: list[float] = []

    def generate(self, request: EngineRequest) -> EngineGeneration:
        self.temperatures.append(request.temperature)
        index: int = len(self.temperatures) - 1
        payload: dict[str, str] = self._writes[min(index, len(self._writes) - 1)]
        for relative, body in payload.items():
            path: Path = request.workdir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        if self._fail_format:
            return EngineGeneration(format_ok=False, format_error="invalid JSON")
        return EngineGeneration(format_ok=True, raw_output="ok")


class _ClockEngine:
    name: str = "clock"

    def __init__(self, clock: dict[str, float]) -> None:
        self._clock: dict[str, float] = clock
        self.calls: int = 0

    def generate(self, request: EngineRequest) -> EngineGeneration:
        self.calls += 1
        self._clock["t"] += 10.0
        return EngineGeneration(format_ok=False, format_error="nope")


class _FakeModel:
    def __init__(self, content: str) -> None:
        self._content: str = content
        self.temperatures: list[float] = []

    def set_temperature(self, temperature: float) -> None:
        self.temperatures.append(temperature)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        del messages, model
        return ModelResponse(content=self._content, model="fake")

    def is_available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["fake"]


def test_best_of_cap_does_not_multiply_local_retries() -> None:
    assert BEST_OF_N == 5
    assert MAX_GENERATIONS_PER_TASK == 5
    assert MAX_GENERATIONS_PER_TASK < BEST_OF_N * DEFAULT_MAX_RETRIES
    assert BEST_OF_TEMPERATURES == (0.0, 0.2, 0.4, 0.6, 0.8)
    assert MAX_SECONDS_PER_TASK == 600.0
    assert MAX_SECONDS_PER_GENERATION == 240.0


def test_best_of_stops_at_first_pass_and_records_both_rates(tmp_path: Path) -> None:
    engine = _ScriptedEngine(
        [
            {"src/ok.py": "bad\n"},
            {"src/ok.py": "bad\n"},
            {"src/ok.py": "ok\n"},
            {"src/ok.py": "ok\n"},
        ]
    )
    result = run_best_of(
        engine,
        prompt="write ok",
        editable_files=("src/ok.py",),
        test_command="python3 -c \"import pathlib; assert pathlib.Path('src/ok.py').read_text()=='ok\\n'\"",
        workdir=tmp_path,
    )
    assert result.passed_at_1 is False
    assert result.passed_best is True
    assert result.stop_reason == "pass"
    assert engine.temperatures == [0.0, 0.2, 0.4]
    assert (tmp_path / "src" / "ok.py").read_text(encoding="utf-8") == "ok\n"


def test_best_of_uses_five_samples_when_none_pass(tmp_path: Path) -> None:
    engine = _ScriptedEngine([{"src/ok.py": "bad\n"}])
    result = run_best_of(
        engine,
        prompt="write ok",
        editable_files=("src/ok.py",),
        test_command="python3 -c \"import pathlib; assert pathlib.Path('src/ok.py').read_text()=='ok\\n'\"",
        workdir=tmp_path,
    )
    assert result.passed_at_1 is False
    assert result.passed_best is False
    assert result.stop_reason == "exhausted"
    assert engine.temperatures == [0.0, 0.2, 0.4, 0.6, 0.8]
    assert not (tmp_path / "src" / "ok.py").exists()


def test_time_cap_stops_before_the_generation_cap(tmp_path: Path) -> None:
    clock_state: dict[str, float] = {"t": 0.0}
    engine = _ClockEngine(clock_state)
    result = run_best_of(
        engine,
        prompt="write",
        editable_files=("src/ok.py",),
        test_command="python3 -c 'raise SystemExit(1)'",
        workdir=tmp_path,
        max_seconds=15.0,
        clock=lambda: clock_state["t"],
    )
    assert engine.calls == 2
    assert result.stop_reason == "time_cap"
    assert result.passed_best is False


def test_locked_path_change_is_rejected_and_restored(tmp_path: Path) -> None:
    locked: Path = tmp_path / "tests" / "locked.py"
    locked.parent.mkdir(parents=True)
    locked.write_text("LOCKED\n", encoding="utf-8")
    engine = _ScriptedEngine(
        [{"src/ok.py": "ok\n", "tests/locked.py": "TAMPERED\n"}]
    )
    result = run_best_of(
        engine,
        prompt="do not touch tests",
        editable_files=("src/ok.py",),
        test_command="python3 -c \"import pathlib; assert pathlib.Path('src/ok.py').read_text()=='ok\\n'\"",
        workdir=tmp_path,
        max_generations=1,
    )
    assert result.passed_at_1 is False
    assert result.samples[0].reason == "locked path"
    assert locked.read_text(encoding="utf-8") == "LOCKED\n"
    assert not (tmp_path / "src" / "ok.py").exists()


def test_scorecard_separates_pass_at_1_and_pass_at_5() -> None:
    rows = aggregate_best_of(
        [
            BestOfTaskResult("roop", "easy", "a", True, True, 1, 2.0, 0, ""),
            BestOfTaskResult("roop", "easy", "b", False, True, 3, 4.0, 1, ""),
            BestOfTaskResult("roop", "medium", "c", False, False, 5, 6.0, 2, "missing module"),
            BestOfTaskResult("roop", "medium", "d", False, False, 5, 8.0, 0, "missing module"),
            BestOfTaskResult("roop", "medium", "e", False, False, 2, 3.0, 0, "assertion"),
        ]
    )
    rendered = render_best_of_scorecard(rows)
    assert "pass_at_1_rate" in rendered
    assert "pass_at_5_rate" in rendered
    easy = rows[0]
    assert easy.difficulty == "easy"
    assert easy.pass_at_1_rate == 0.5
    assert easy.pass_at_5_rate == 1.0
    assert easy.format_error_rate == 0.25
    assert top_failure_reasons(
        [
            BestOfTaskResult("roop", "medium", "c", False, False, 5, 1, 0, "missing module"),
            BestOfTaskResult("roop", "medium", "d", False, False, 5, 1, 0, "missing module"),
            BestOfTaskResult("roop", "medium", "e", False, False, 2, 1, 0, "assertion"),
            BestOfTaskResult("roop", "medium", "f", False, False, 1, 1, 0, "format: invalid JSON"),
        ]
    ) == [("missing module", 2), ("assertion", 1), ("format: invalid JSON", 1)]


def test_roop_engine_writes_a_new_file_at_the_sample_temperature(tmp_path: Path) -> None:
    model = _FakeModel(
        '{"files":[{"path":"src/demo.py","content":"VALUE = 1\\n"}]}'
    )
    engine = RoopEngine(model)
    generation = engine.generate(
        EngineRequest(
            prompt="Create src/demo.py",
            editable_files=("src/demo.py",),
            test_command="python3 -m unittest discover -s tests -p test_demo.py -v",
            workdir=tmp_path,
            temperature=0.4,
        )
    )
    assert generation.format_ok is True
    assert model.temperatures == [0.4]
    assert (tmp_path / "src" / "demo.py").read_text(encoding="utf-8") == "VALUE = 1\n"
