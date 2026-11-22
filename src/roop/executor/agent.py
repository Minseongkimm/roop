"""Local Agent Executor — model call + harness side effects (Phase 4)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from roop.adapters.model import ChatMessage, ModelAdapter, ModelResponse
from roop.adapters.ollama import OllamaClient
from roop.context.builder import BuildResult, ContextBuilder, ContextPacket
from roop.context.roles import AgentRole
from roop.executor.json_util import parse_json_object
from roop.harness.fs_guard import WriteGuard
from roop.harness.tools import CommandResult, FileTransaction, PatchResult, ToolHarness
from roop.orchestrator.tasks import Task, TaskStore


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Outcome of one agent role execution."""

    role: AgentRole
    task_id: int
    ok: bool
    model_raw: str
    parsed: dict[str, Any]
    patches: list[PatchResult] = field(default_factory=list)
    command: CommandResult | None = None
    enqueued_task_ids: list[int] = field(default_factory=list)
    message: str = ""
    packet_path: str | None = None
    transaction: FileTransaction | None = field(default=None, compare=False, repr=False)


class AgentExecutor:
    """Run one role tick: packet → model → parse → harness."""

    def __init__(
        self,
        project_root: Path,
        store: TaskStore,
        *,
        model: ModelAdapter | None = None,
        dry_run: bool = False,
    ) -> None:
        self._project_root: Path = project_root.resolve()
        self._store: TaskStore = store
        self._model: ModelAdapter = model or OllamaClient(timeout_seconds=120.0)
        self._dry_run: bool = dry_run
        self._builder: ContextBuilder = ContextBuilder(self._project_root)

    def execute(
        self,
        task: Task,
        role: AgentRole,
        *,
        verifier_feedback: str = "",
    ) -> ExecutionResult:
        build: BuildResult = self._builder.build_and_write(
            task,
            role,
            verifier_feedback=verifier_feedback,
        )
        packet: ContextPacket = build.packet
        packet_path: str | None = (
            str(build.markdown_path) if build.markdown_path else None
        )
        raw: str
        if self._dry_run:
            raw = _dry_run_payload(role=role, task=task)
        else:
            response: ModelResponse = self._model.chat(_messages_from_packet(packet))
            raw = response.content
        self._persist_raw(task_id=task.id, role=role, raw=raw, suffix="raw")
        try:
            parsed: dict[str, Any] = parse_json_object(raw)
        except ValueError:
            # one regenerate attempt
            if self._dry_run:
                return ExecutionResult(
                    role=role,
                    task_id=task.id,
                    ok=False,
                    model_raw=raw,
                    parsed={},
                    message="JSON parse failed",
                    packet_path=packet_path,
                )
            retry: ModelResponse = self._model.chat(
                list(_messages_from_packet(packet))
                + [
                    ChatMessage(
                        role="user",
                        content=(
                            "Previous output was invalid. Reply with ONE JSON object only. "
                            'Coder schema: {"files":[{"path":"...","content":"..."}]}'
                        ),
                    )
                ]
            )
            raw = retry.content
            self._persist_raw(task_id=task.id, role=role, raw=raw, suffix="raw-retry")
            try:
                parsed = parse_json_object(raw)
            except ValueError as err:
                return ExecutionResult(
                    role=role,
                    task_id=task.id,
                    ok=False,
                    model_raw=raw,
                    parsed={},
                    message=f"JSON parse failed after retry: {err}",
                    packet_path=packet_path,
                )
        return self._apply_parsed(
            task=task,
            role=role,
            raw=raw,
            parsed=parsed,
            packet_path=packet_path,
        )

    def _persist_raw(
        self,
        *,
        task_id: int,
        role: AgentRole,
        raw: str,
        suffix: str,
    ) -> None:
        relative: Path = (
            Path(WriteGuard.AGENT_DIR_NAME)
            / "packets"
            / f"task-{task_id}-{role.value}.{suffix}.txt"
        )
        WriteGuard(self._project_root).write_text(relative, raw)

    def _apply_parsed(
        self,
        *,
        task: Task,
        role: AgentRole,
        raw: str,
        parsed: dict[str, Any],
        packet_path: str | None,
    ) -> ExecutionResult:
        guard: WriteGuard = WriteGuard(self._project_root).with_allow_paths(
            task.allow_paths
        )
        tools: ToolHarness = ToolHarness(self._project_root, guard)
        if role == AgentRole.PLANNER:
            return self._apply_planner(
                task=task,
                raw=raw,
                parsed=parsed,
                packet_path=packet_path,
            )
        if role == AgentRole.CODER:
            transaction = FileTransaction(self._project_root)
            try:
                return self._apply_coder(
                    task=task,
                    tools=tools,
                    raw=raw,
                    parsed=parsed,
                    packet_path=packet_path,
                    transaction=transaction,
                )
            except Exception:
                transaction.rollback()
                raise
        if role == AgentRole.REVIEWER:
            blocking: Any = parsed.get("blocking_issues", parsed.get("issues", []))
            count: int = len(blocking) if isinstance(blocking, list) else 1
            approved: bool = bool(parsed.get("approved", count == 0))
            return ExecutionResult(
                role=role,
                task_id=task.id,
                ok=approved and count == 0,
                model_raw=raw,
                parsed=parsed,
                message="review approved" if approved and count == 0 else "review blocked",
                packet_path=packet_path,
            )
        # tester
        command_text: str = str(
            parsed.get("verify_command")
            or parsed.get("command")
            or task.verify_command
            or ""
        )
        command: CommandResult | None = None
        if command_text and not self._dry_run:
            command = tools.run_command(command_text)
        elif command_text and self._dry_run:
            command = CommandResult(
                command=command_text,
                exit_code=0,
                stdout="dry-run skip",
                stderr="",
            )
        ok: bool = command.ok if command is not None else bool(command_text)
        return ExecutionResult(
            role=role,
            task_id=task.id,
            ok=ok,
            model_raw=raw,
            parsed=parsed,
            command=command,
            message=(
                f"tester exit={command.exit_code}" if command else "tester: no command"
            ),
            packet_path=packet_path,
        )

    def _apply_planner(
        self,
        *,
        task: Task,
        raw: str,
        parsed: dict[str, Any],
        packet_path: str | None,
    ) -> ExecutionResult:
        created_ids: list[int] = []
        tasks_raw: Any = parsed.get("tasks", [])
        if isinstance(tasks_raw, list):
            for item in tasks_raw:
                if not isinstance(item, dict):
                    continue
                title: str = str(item.get("title") or item.get("goal") or "").strip()
                if not title:
                    continue
                child = self._store.create_task(
                    title,
                    description=str(item.get("description") or ""),
                    feature_ids=str(
                        item.get("feature_ids") or task.feature_ids or ""
                    ),
                    allow_paths=str(item.get("allow_paths") or task.allow_paths),
                    acceptance_criteria=str(
                        item.get("acceptance_criteria")
                        or item.get("ac")
                        or ""
                    ),
                    verify_command=str(item.get("verify_command") or ""),
                    priority=int(item.get("priority") or task.priority),
                    depends_on=_as_int_list(item.get("depends_on")),
                )
                created_ids.append(child.id)
        return ExecutionResult(
            role=AgentRole.PLANNER,
            task_id=task.id,
            ok=True,
            model_raw=raw,
            parsed=parsed,
            enqueued_task_ids=created_ids,
            message=f"planner enqueued {len(created_ids)} task(s)",
            packet_path=packet_path,
        )

    def _apply_coder(
        self,
        *,
        task: Task,
        tools: ToolHarness,
        raw: str,
        parsed: dict[str, Any],
        packet_path: str | None,
        transaction: FileTransaction | None = None,
    ) -> ExecutionResult:
        patches: list[PatchResult] = []
        files: Any = parsed.get("files") or parsed.get("patches") or []
        if isinstance(files, dict):
            files = [files]
        if not isinstance(files, list):
            files = []
        # single-file shorthand
        if not files and parsed.get("path"):
            files = [parsed]
        for item in files:
            if not isinstance(item, dict):
                continue
            path: str = str(item.get("path") or item.get("file") or "").strip()
            if not path:
                continue
            if transaction is not None:
                transaction.capture(path)
            if "content" in item:
                patches.append(tools.write_file(path, str(item.get("content") or "")))
                continue
            find: str = str(item.get("find") or item.get("old") or "")
            replace: str = str(item.get("replace") or item.get("new") or item.get("hunk") or "")
            patches.append(
                tools.apply_unified_hunk(path, find=find, replace=replace)
            )
        applied: int = sum(1 for item in patches if item.applied)
        ok: bool = applied > 0 and all(item.applied for item in patches)
        if not patches:
            ok = False
        return ExecutionResult(
            role=AgentRole.CODER,
            task_id=task.id,
            ok=ok,
            model_raw=raw,
            parsed=parsed,
            patches=patches,
            message=f"coder applied {applied}/{len(patches)} patch(es)",
            packet_path=packet_path,
            transaction=transaction,
        )


def _messages_from_packet(packet: ContextPacket) -> Sequence[ChatMessage]:
    user_parts: list[str] = [
        "## Task JSON",
        json.dumps(packet.task, ensure_ascii=False, indent=2),
    ]
    if packet.project_rules:
        user_parts.extend(["## Project rules", packet.project_rules])
    if packet.project_context:
        user_parts.extend(["## Project context", packet.project_context])
    if packet.feature_context:
        user_parts.extend(["## Feature context", packet.feature_context])
    if packet.code_slices:
        user_parts.append("## Code slices")
        for item in packet.code_slices:
            user_parts.append(f"### {item.path}\n```\n{item.content}\n```")
    if packet.verifier_feedback:
        user_parts.extend(["## Verifier feedback", packet.verifier_feedback])
    if packet.role == AgentRole.CODER:
        user_parts.append(
            "Respond with a single JSON object only, schema:\n"
            '{"files":[{"path":"relative/path.md","content":"full file contents"}]}\n'
            "path must be inside allow_paths. Prefer writing the full file content."
        )
    else:
        user_parts.append("Respond with a single JSON object only.")
    return [
        ChatMessage(role="system", content=packet.system_prompt),
        ChatMessage(role="user", content="\n\n".join(user_parts)),
    ]


def _dry_run_payload(*, role: AgentRole, task: Task) -> str:
    if role == AgentRole.PLANNER:
        return json.dumps(
            {
                "tasks": [
                    {
                        "title": f"implement: {task.title}",
                        "allow_paths": task.allow_paths,
                        "acceptance_criteria": task.acceptance_criteria
                        or "done",
                        "verify_command": task.verify_command,
                    }
                ]
            }
        )
    if role == AgentRole.CODER:
        return json.dumps(
            {
                "files": [
                    {
                        "path": ".agent/scratch/dry-run.txt",
                        "content": f"dry-run patch for task {task.id}: {task.title}\n",
                    }
                ]
            }
        )
    if role == AgentRole.REVIEWER:
        return json.dumps({"approved": True, "blocking_issues": []})
    return json.dumps(
        {"verify_command": task.verify_command or "true", "notes": "dry-run"}
    )


def _as_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.isdigit():
            result.append(int(item))
    return result
