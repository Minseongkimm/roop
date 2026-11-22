"""Roop coding engine: one executor pass. The harness grades the files."""

from __future__ import annotations

from roop.adapters.model import ModelAdapter
from roop.adapters.ollama import DEFAULT_MODEL, DEFAULT_NUM_CTX, OllamaClient
from roop.engines.budget import MAX_SECONDS_PER_GENERATION
from roop.context.roles import AgentRole
from roop.engines.base import EngineGeneration, EngineRequest
from roop.executor.agent import AgentExecutor, ExecutionResult
from roop.orchestrator.tasks import Task, TaskStore


class RoopEngine:
    """Adapt the existing coder executor to ``CodingEngine``."""

    name: str = "roop"

    def __init__(self, model: ModelAdapter | None = None) -> None:
        self._model: ModelAdapter = model or OllamaClient(
            timeout_seconds=MAX_SECONDS_PER_GENERATION,
            default_model=DEFAULT_MODEL,
            num_ctx=DEFAULT_NUM_CTX,
        )

    def generate(self, request: EngineRequest) -> EngineGeneration:
        setter = getattr(self._model, "set_temperature", None)
        if callable(setter):
            setter(request.temperature)
        store: TaskStore = TaskStore(request.workdir / ".agent" / "engine-task.sqlite3")
        task: Task = store.create_task(
            "engine sample",
            description=request.prompt,
            allow_paths=",".join(request.editable_files) or "src/**",
            acceptance_criteria="The harness runs the test command.",
            verify_command=request.test_command,
            feature_ids="eval",
        )
        executor: AgentExecutor = AgentExecutor(
            request.workdir,
            store,
            model=self._model,
        )
        execution: ExecutionResult = executor.execute(task, AgentRole.CODER)
        applied: bool = any(item.applied for item in execution.patches)
        if execution.transaction is not None:
            if applied:
                execution.transaction.commit()
            else:
                execution.transaction.rollback()
        if not execution.parsed:
            return EngineGeneration(
                format_ok=False,
                format_error=execution.message or "invalid JSON",
                raw_output=execution.model_raw,
            )
        if not applied:
            return EngineGeneration(
                format_ok=False,
                format_error=execution.message or "no editable file changed",
                raw_output=execution.model_raw,
            )
        return EngineGeneration(format_ok=True, raw_output=execution.model_raw)


def task_prompt(description: str, editable_files: tuple[str, ...], test_command: str) -> str:
    """Build the prompt both engines receive."""
    files: str = "\n".join(f"- {path}" for path in editable_files)
    return (
        f"{description.strip()}\n\n"
        "Editable files, create or edit every one of these and no others:\n"
        f"{files}\n\n"
        f"Test command, read-only: {test_command}\n"
        "Do not create or modify tests."
    )
