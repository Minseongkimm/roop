"""API fallback after two local verification failures, plus scorecard fields."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from roop.adapters.api import (
    DEFAULT_API_MODEL,
    ApiClient,
    api_client_from_env,
    estimate_cost_usd,
    read_api_key,
    should_hand_off_to_api,
)
from roop.adapters.model import ChatMessage, ModelResponse
from roop.context.roles import AgentRole
from roop.eval.scorecard import build_scorecard, render_scorecard, summarize_rounds
from roop.orchestrator.loop import OrchestratorLoop
from roop.orchestrator.tasks import TaskStatus, TaskStore


def test_handoff_is_only_for_hard_after_two_local_failures() -> None:
    assert should_hand_off_to_api(
        local_verify_failures=1, dry_run=False, difficulty="hard"
    ) is False
    assert should_hand_off_to_api(
        local_verify_failures=2, dry_run=False, difficulty="hard"
    ) is True
    assert should_hand_off_to_api(
        local_verify_failures=5, dry_run=True, difficulty="hard"
    ) is False
    assert should_hand_off_to_api(
        local_verify_failures=5, dry_run=False, difficulty="easy"
    ) is False
    assert should_hand_off_to_api(
        local_verify_failures=5, dry_run=False, difficulty="medium"
    ) is False


def test_default_model_is_cheap() -> None:
    assert DEFAULT_API_MODEL.endswith("mini")
    assert "opus" not in DEFAULT_API_MODEL
    assert DEFAULT_API_MODEL != "gpt-4o"


def test_read_api_key_from_env_only(monkeypatch) -> None:
    monkeypatch.setenv("ROOP_API_KEY", "roop-test")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    assert read_api_key() == "roop-test"
    monkeypatch.delenv("ROOP_API_KEY")
    assert read_api_key() == "openai-test"
    monkeypatch.delenv("OPENAI_API_KEY")
    assert read_api_key() == ""
    assert api_client_from_env() is None


def test_api_client_records_usage_and_cost() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == DEFAULT_API_MODEL
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "model": DEFAULT_API_MODEL,
                "choices": [{"message": {"content": "{\"ok\": true}"}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
            },
        )

    client = ApiClient(api_key="test-key", transport=httpx.MockTransport(handler))
    response = client.chat([ChatMessage(role="user", content="hi")])
    assert response.provider == "api"
    assert response.input_tokens == 1000
    assert response.output_tokens == 500
    assert client.calls == 1
    expected = estimate_cost_usd(1000, 500)
    assert response.estimated_cost_usd == expected
    assert client.estimated_cost_usd == expected


def test_two_local_failures_then_api_pass(tmp_path: Path) -> None:
    local_calls = {"n": 0}

    class LocalModel:
        def chat(self, messages, *, model=None):
            local_calls["n"] += 1
            return ModelResponse(
                content=(
                    '{"files":[{"path":"src/x.py","content":"bad-'
                    + str(local_calls["n"])
                    + '\\n"}]}'
                ),
                model="qwen2.5-coder:7b",
                provider="local",
            )

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["qwen2.5-coder:7b"]

    class ApiModel:
        def __init__(self) -> None:
            self.calls = 0
            self.estimated_cost_usd = 0.0

        def chat(self, messages, *, model=None):
            self.calls += 1
            self.estimated_cost_usd += 0.001
            return ModelResponse(
                content='{"files":[{"path":"src/x.py","content":"ok\\n"}]}',
                model="gpt-4o-mini",
                provider="api",
                estimated_cost_usd=0.001,
            )

        def is_available(self) -> bool:
            return True

        def list_models(self) -> list[str]:
            return ["gpt-4o-mini"]

    project = tmp_path / "app"
    (project / "src").mkdir(parents=True)
    (project / ".agent" / "project").mkdir(parents=True)
    (project / ".agent" / "project" / "overview.md").write_text("x\n", encoding="utf-8")
    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "write x",
        feature_ids="eval,hard,demo",
        allow_paths="src/**",
        verify_command=(
            "python3 -c \"from pathlib import Path; "
            "assert Path('src/x.py').read_text().strip()=='ok'\""
        ),
        max_retries=3,
    )
    api = ApiModel()
    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        model=LocalModel(),
        api_model=api,
    )
    first = loop.tick()
    second = loop.tick()
    assert first.green is False
    assert second.green is False
    assert api.calls == 0
    assert store.get_task(1).local_verify_failures == 2
    assert store.get_task(1).status == TaskStatus.PENDING
    third = loop.tick()
    assert third.green is True
    assert local_calls["n"] == 2
    assert api.calls == 1
    task = store.get_task(1)
    assert task.outcome == "api_pass"
    assert task.api_calls == 1
    assert task.estimated_cost_usd == 0.001
    rows = build_scorecard(db)
    assert rows[0].difficulty == "hard"
    assert rows[0].api_pass == 1
    assert rows[0].local_pass == 0
    assert rows[0].api_calls == 1
    rendered = render_scorecard(rows, engine_commit="abc")
    assert "api_pass" in rendered
    assert "0.001000" in rendered
    summary = summarize_rounds(project / ".agent" / "runs" / "rounds.jsonl")
    assert "api_pass=1" in summary
    assert "api_calls=1" in summary


def test_missing_api_key_records_api_skipped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ROOP_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class LocalModel:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages, *, model=None):
            self.calls += 1
            return ModelResponse(
                content=(
                    '{"files":[{"path":"src/x.py","content":"bad-'
                    + str(self.calls)
                    + '\\n"}]}'
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
    (project / ".agent" / "project" / "overview.md").write_text("x\n", encoding="utf-8")
    db = project / ".agent" / "tasks.sqlite3"
    store = TaskStore(db)
    store.create_task(
        "write x",
        feature_ids="eval,hard,demo",
        allow_paths="src/**",
        verify_command="false",
        max_retries=3,
    )
    local = LocalModel()
    loop = OrchestratorLoop.from_database(
        db,
        project_root=project,
        role=AgentRole.CODER,
        execute=True,
        model=local,
    )
    loop.tick()
    loop.tick()
    third = loop.tick()
    assert "API_SKIPPED" in third.message
    assert local.calls == 2
    task = store.get_task(1)
    assert task.status == TaskStatus.BLOCKED
    assert task.outcome == "api_skipped"
    assert task.api_calls == 0
    row = json.loads(
        (project / ".agent" / "runs" / "rounds.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )
    assert row["outcome"] == "api_skipped"
    assert row["provider"] == "none"
    assert row["api_calls"] == 0
    card = build_scorecard(db)[0]
    assert card.api_skipped == 1
    assert card.fail == 0
    assert card.local_pass == 0
