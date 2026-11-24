"""Headless process-group runs, OpenRouter usage, and hard caps. No live API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from roop.engines.aider_engine import AiderEngine, run_process_group
from roop.engines.base import EngineGeneration, EngineRequest
from roop.engines.routing import (
    ModelSpec,
    RouteConfig,
    build_routed_engine,
    fetch_openrouter_generation,
    local_attempts,
)
from roop.engines.usage import usage_from_openrouter, usage_from_text
from roop.eval.retry_eval import run_retry_eval
from roop.eval.suite import load_suite
from roop.eval.worktree import ensure_task_worktree


def test_timeout_kills_the_child_process_group(tmp_path: Path) -> None:
    marker: Path = tmp_path / "pids"
    script: Path = tmp_path / "hang.py"
    script.write_text(
        "import os, pathlib, subprocess, time\n"
        "child = subprocess.Popen(['sleep', '60'])\n"
        f"pathlib.Path({str(marker)!r}).write_text(str(os.getpid()) + '\\n' + str(child.pid))\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    try:
        run_process_group([sys.executable, str(script)], cwd=tmp_path, timeout=2)
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError("the hanging process group should have timed out")
    parent_pid, child_pid = (int(line) for line in marker.read_text(encoding="utf-8").splitlines())
    deadline: float = time.time() + 3
    while time.time() < deadline and (_alive(parent_pid) or _alive(child_pid)):
        time.sleep(0.05)
    assert not _alive(parent_pid)
    assert not _alive(child_pid)


def test_generate_closes_stdin(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["stdin"] = kwargs["stdin"]
        workdir: Path = kwargs["cwd"]  # type: ignore[assignment]
        (workdir / "src" / "a.py").write_text("x\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="edited", stderr="")

    AiderEngine(binary="aider", runner=runner).generate(
        EngineRequest(
            prompt="edit",
            editable_files=("src/a.py",),
            test_command="true",
            workdir=tmp_path,
        )
    )
    assert seen["stdin"] is subprocess.DEVNULL


def test_openrouter_cost_is_split_and_price_table_fills_gaps() -> None:
    reported = usage_from_openrouter(
        "openai/qwen/qwen3-coder",
        {
            "id": "gen-1",
            "model": "qwen/qwen3-coder",
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 100,
                "cost": 0.0005,
                "prompt_tokens_details": {"cached_tokens": 200},
            },
        },
    )
    assert reported.input_tokens == 1200
    assert reported.cached_tokens == 200
    assert reported.provider_cost_usd > 0
    assert reported.cache_cost_usd > 0
    assert reported.provider_cost_usd != reported.cache_cost_usd
    assert abs(reported.cost_usd - 0.0005) < 1e-12
    priced = usage_from_openrouter(
        "qwen/qwen3-coder",
        {"usage": {"prompt_tokens": 1000, "completion_tokens": 0, "prompt_tokens_details": {"cached_tokens": 0}}},
    )
    assert abs(priced.cost_usd - (1000 * 0.0000003)) < 1e-12
    assert priced.cache_cost_usd == 0
    local = usage_from_text("no usage here", model="ollama_chat/qwen2.5-coder:7b")
    assert local.cost_usd == 0
    generation = usage_from_openrouter(
        "qwen/qwen3-coder",
        {
            "data": {
                "id": "gen-2",
                "model": "qwen/qwen3-coder",
                "native_tokens_prompt": 10,
                "native_tokens_completion": 4,
                "native_tokens_cached": 10,
                "usage": 0.0002,
            }
        },
    )
    assert generation.cached_tokens == 10
    assert generation.cache_cost_usd > 0
    assert generation.provider_cost_usd > 0
    assert abs(generation.cost_usd - 0.0002) < 1e-12


def test_generation_lookup_uses_the_header_not_the_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/generation")
        assert request.url.params["id"] == "gen-abc"
        assert request.headers["authorization"] == "Bearer test-key"
        assert "test-key" not in str(request.url)
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "gen-abc",
                    "model": "qwen/qwen3-coder",
                    "tokens_prompt": 8,
                    "tokens_completion": 2,
                    "native_tokens_cached": 0,
                    "usage": 0.00001,
                }
            },
        )

    payload = fetch_openrouter_generation(
        "gen-abc",
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
    )
    usage = usage_from_openrouter("qwen/qwen3-coder", payload)
    assert usage.input_tokens == 8
    assert usage.output_tokens == 2
    assert usage.cost_usd == 0.00001
    assert usage.cache_cost_usd == 0


def test_engine_fills_cost_from_a_mocked_generation_lookup(tmp_path: Path) -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        workdir: Path = kwargs["cwd"]  # type: ignore[assignment]
        (workdir / "src" / "a.py").write_text("x\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="id gen-zzz\n", stderr="")

    def lookup(generation_id: str) -> dict[str, object]:
        assert generation_id == "gen-zzz"
        return {
            "model": "qwen/qwen3-coder",
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cost": 0.00004},
        }

    generation = AiderEngine(
        binary="aider",
        model="openai/qwen/qwen3-coder",
        num_ctx=None,
        runner=runner,
        usage_lookup=lookup,
    ).generate(
        EngineRequest(prompt="p", editable_files=("src/a.py",), test_command="true", workdir=tmp_path)
    )
    assert generation.input_tokens == 10
    assert generation.cost_usd == 0.00004
    assert generation.provider_cost_usd == 0.00004


def test_route_accepts_ollama_base_and_openrouter_fallback(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    config = RouteConfig(
        base=ModelSpec(name="qwen2.5-coder:7b"),
        fallback=ModelSpec(
            name="qwen/qwen3-coder",
            base_url="https://openrouter.ai/api/v1",
            key_env="OPENROUTER_API_KEY",
        ),
    )
    assert config.problem() == ""
    assert local_attempts(config) == (2, 1)
    seen: dict[str, object] = {}

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["command"] = command
        seen["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    base = build_routed_engine(config.base, timeout_seconds=600, binary="aider", runner=runner)
    fallback = build_routed_engine(config.fallback, timeout_seconds=600, binary="aider", runner=runner)  # type: ignore[arg-type]
    base.generate(EngineRequest(prompt="p", editable_files=("src/a.py",), test_command="true", workdir=tmp_path))
    assert seen["command"][seen["command"].index("--model") + 1] == "ollama_chat/qwen2.5-coder:7b"  # type: ignore[index,union-attr]
    fallback.generate(
        EngineRequest(prompt="p", editable_files=("src/a.py",), test_command="true", workdir=tmp_path / "fb")
    )
    command = seen["command"]
    assert isinstance(command, list)
    assert command[command.index("--model") + 1] == "openai/qwen/qwen3-coder"
    assert "test-key" not in " ".join(command)
    env = seen["env"]
    assert isinstance(env, dict)
    assert env["OPENAI_API_BASE"] == "https://openrouter.ai/api/v1"
    assert env["OPENAI_API_KEY"] == "test-key"


def test_task_worktrees_do_not_share_files(tmp_path: Path) -> None:
    alpha: Path = ensure_task_worktree(tmp_path, "alpha")
    beta: Path = ensure_task_worktree(tmp_path, "beta")
    (alpha / "src").mkdir()
    (alpha / "src" / "only.py").write_text("alpha\n", encoding="utf-8")
    assert not (beta / "src" / "only.py").exists()
    assert (alpha / ".git").is_file()
    assert _git_common(alpha) == _git_common(beta)


def test_attempt_cap_stops_one_task_and_the_queue_continues(tmp_path: Path) -> None:
    calls: list[str] = []

    class Fail:
        name = "fail"

        def generate(self, request: EngineRequest) -> EngineGeneration:
            calls.append(request.workdir.name)
            return EngineGeneration(format_ok=False, format_error="no edit", model="ollama_chat/qwen2.5-coder:7b")

    rows = run_retry_eval(
        engine=Fail(),
        suite=_suite(tmp_path),
        workspace=tmp_path / "run",
        split="heldout",
        max_local_attempts=1,
    )
    assert [row["task_id"] for row in rows] == ["one", "two"]
    assert [row["stop_reason"] for row in rows] == ["attempt_cap", "attempt_cap"]
    assert calls == ["one", "two"]


def test_cost_cap_does_not_start_the_next_task(tmp_path: Path) -> None:
    class Spend:
        name = "spend"

        def generate(self, request: EngineRequest) -> EngineGeneration:
            return EngineGeneration(
                format_ok=False,
                format_error="no edit",
                model="qwen/qwen3-coder",
                input_tokens=1000,
                output_tokens=100,
                cached_tokens=200,
                provider_cost_usd=4.0,
                cache_cost_usd=1.0,
                cost_usd=5.0,
            )

    rows = run_retry_eval(
        engine=Spend(),
        suite=_suite(tmp_path),
        workspace=tmp_path / "run",
        split="heldout",
        max_local_attempts=3,
        max_cost_usd=5,
    )
    assert [row["task_id"] for row in rows] == ["one"]
    attempt = rows[0]["attempts"][0]
    assert attempt["model"] == "qwen/qwen3-coder"
    assert attempt["input_tokens"] == 1000
    assert attempt["cached_tokens"] == 200
    assert attempt["provider_cost_usd"] == 4.0
    assert attempt["cache_cost_usd"] == 1.0
    assert attempt["cost_usd"] == 5.0
    assert rows[0]["stop_reason"] == "attempt_cap"
    state = json.loads((tmp_path / "run" / "run_state.json").read_text(encoding="utf-8"))
    assert state["stop_reason"] == "cost_cap"
    assert state["skipped"] == ["two"]
    summary = (tmp_path / "run" / "summary.txt").read_text(encoding="utf-8")
    assert "run_stop: cost_cap" in summary
    assert "skipped=two" in summary


def _suite(tmp_path: Path):
    manifest = tmp_path / "suite.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "tiny",
                "tasks": [
                    _task("one"),
                    _task("two"),
                ],
            }
        ),
        encoding="utf-8",
    )
    return load_suite(manifest)


def _task(task_id: str) -> dict[str, object]:
    return {
        "id": task_id,
        "title": task_id,
        "difficulty": "easy",
        "split": "heldout",
        "description": "edit",
        "verify_command": "python3 -c \"raise SystemExit(1)\"",
        "src_files": ["src/a.py"],
    }


def _git_common(task: Path) -> Path:
    raw: str = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=task, text=True).strip()
    path: Path = Path(raw)
    if not path.is_absolute():
        path = task / path
    return path.resolve()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
