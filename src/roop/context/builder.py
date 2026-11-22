"""Assemble narrow role packets from Task + ``.agent/`` docs (Phase 3)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from roop.context.budget import (
    DEFAULT_TOKEN_BUDGET,
    estimate_tokens,
    truncate_to_tokens,
)
from roop.context.roles import AgentRole, get_role_prompt
from roop.harness.fs_guard import WriteGuard
from roop.orchestrator.tasks import Task

MAX_CONVENTIONS_CHARS: int = 2500
MAX_FEATURE_CHARS: int = 2000
MAX_SLICE_CHARS: int = 2400
MAX_SLICES: int = 3
MAX_FEEDBACK_CHARS: int = 1200
RG_TIMEOUT_SECONDS: float = 5.0


@dataclass(frozen=True, slots=True)
class CodeSlice:
    """A narrow file excerpt for the packet."""

    path: str
    content: str
    tokens: int


@dataclass(frozen=True, slots=True)
class ContextPacket:
    """Role-scoped context packet ready for a model call (Phase 4)."""

    role: AgentRole
    task_id: int
    system_prompt: str
    task: dict[str, Any]
    project_rules: str
    feature_context: str
    code_slices: list[CodeSlice] = field(default_factory=list)
    verifier_feedback: str = ""
    token_budget: int = DEFAULT_TOKEN_BUDGET
    estimated_tokens: int = 0
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = asdict(self)
        payload["role"] = self.role.value
        return payload

    def render_markdown(self) -> str:
        slices_md: list[str] = []
        for item in self.code_slices:
            slices_md.append(
                f"### `{item.path}` ({item.tokens} tok)\n\n```\n{item.content}\n```"
            )
        body: str = "\n\n".join(
            [
                f"# Context packet — task {self.task_id} / {self.role.value}",
                f"Budget: {self.estimated_tokens}/{self.token_budget} tokens"
                + (" (truncated)" if self.truncated else ""),
                "## System prompt",
                self.system_prompt,
                "## Task",
                "```json\n" + json.dumps(self.task, ensure_ascii=False, indent=2) + "\n```",
                "## Project rules",
                self.project_rules or "_(none)_",
                "## Feature context",
                self.feature_context or "_(none)_",
                "## Code slices",
                "\n\n".join(slices_md) if slices_md else "_(none)_",
                "## Verifier feedback",
                self.verifier_feedback or "_(none)_",
            ]
        )
        return body.rstrip() + "\n"


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Result of building and optionally persisting a packet."""

    packet: ContextPacket
    json_path: Path | None
    markdown_path: Path | None


class ContextBuilder:
    """Build one role packet from disk knowledge + task row."""

    def __init__(
        self,
        project_root: Path,
        *,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ) -> None:
        self._project_root: Path = project_root.resolve()
        self._agent_root: Path = self._project_root / WriteGuard.AGENT_DIR_NAME
        self._token_budget: int = token_budget
        self._guard: WriteGuard = WriteGuard(self._project_root)

    def build(
        self,
        task: Task,
        role: AgentRole,
        *,
        verifier_feedback: str = "",
        include_code_slices: bool = True,
    ) -> ContextPacket:
        remaining: int = self._token_budget
        truncated: bool = False

        system_prompt: str = get_role_prompt(role)
        remaining -= estimate_tokens(system_prompt)

        task_payload: dict[str, Any] = _task_to_payload(task)
        task_json: str = json.dumps(task_payload, ensure_ascii=False)
        task_tokens: int = estimate_tokens(task_json)
        remaining -= task_tokens

        project_rules: str = _read_agent_text(
            self._agent_root / "project" / "conventions.md",
            max_chars=MAX_CONVENTIONS_CHARS,
        )
        if not project_rules:
            project_rules = _read_agent_text(
                self._agent_root / "project" / "overview.md",
                max_chars=MAX_CONVENTIONS_CHARS,
            )
        project_rules, remaining, hit = _fit_text(project_rules, remaining)
        truncated = truncated or hit

        feature_context: str = _load_feature_context(
            self._agent_root, task.feature_ids
        )
        feature_context, remaining, hit = _fit_text(feature_context, remaining)
        truncated = truncated or hit

        feedback: str = verifier_feedback.strip()
        if feedback:
            feedback = truncate_to_tokens(
                feedback[:MAX_FEEDBACK_CHARS],
                max_tokens=max(0, remaining // 4),
            )
            remaining -= estimate_tokens(feedback)
        else:
            feedback = ""

        slices: list[CodeSlice] = []
        if include_code_slices and role in {AgentRole.CODER, AgentRole.REVIEWER, AgentRole.TESTER}:
            slices, slice_truncated = self._collect_code_slices(
                task=task,
                remaining_tokens=max(0, remaining),
            )
            truncated = truncated or slice_truncated
            remaining -= sum(item.tokens for item in slices)

        used: int = self._token_budget - max(0, remaining)
        return ContextPacket(
            role=role,
            task_id=task.id,
            system_prompt=system_prompt,
            task=task_payload,
            project_rules=project_rules,
            feature_context=feature_context,
            code_slices=slices,
            verifier_feedback=feedback,
            token_budget=self._token_budget,
            estimated_tokens=used,
            truncated=truncated,
        )

    def build_and_write(
        self,
        task: Task,
        role: AgentRole,
        *,
        verifier_feedback: str = "",
        include_code_slices: bool = True,
    ) -> BuildResult:
        packet: ContextPacket = self.build(
            task,
            role,
            verifier_feedback=verifier_feedback,
            include_code_slices=include_code_slices,
        )
        relative_json: Path = (
            Path(WriteGuard.AGENT_DIR_NAME)
            / "packets"
            / f"task-{task.id}-{role.value}.json"
        )
        relative_md: Path = (
            Path(WriteGuard.AGENT_DIR_NAME)
            / "packets"
            / f"task-{task.id}-{role.value}.md"
        )
        json_path: Path = self._guard.write_text(
            relative_json,
            json.dumps(packet.to_dict(), ensure_ascii=False, indent=2) + "\n",
        )
        markdown_path: Path = self._guard.write_text(
            relative_md,
            packet.render_markdown(),
        )
        return BuildResult(
            packet=packet,
            json_path=json_path,
            markdown_path=markdown_path,
        )

    def _collect_code_slices(
        self,
        *,
        task: Task,
        remaining_tokens: int,
    ) -> tuple[list[CodeSlice], bool]:
        if remaining_tokens <= 0:
            return [], True
        query: str = _search_query_from_task(task)
        if not query:
            return [], False
        hits: list[Path] = _rg_files(
            project_root=self._project_root,
            query=query,
            limit=MAX_SLICES,
        )
        slices: list[CodeSlice] = []
        budget_left: int = remaining_tokens
        truncated: bool = False
        per_slice: int = max(200, remaining_tokens // max(1, MAX_SLICES))
        for path in hits:
            if budget_left <= 0:
                truncated = True
                break
            raw: str = _read_file_head(path, max_chars=MAX_SLICE_CHARS)
            if not raw:
                continue
            content: str = truncate_to_tokens(raw, max_tokens=min(per_slice, budget_left))
            tokens: int = estimate_tokens(content)
            if tokens <= 0:
                continue
            rel: str = str(path.relative_to(self._project_root))
            slices.append(CodeSlice(path=rel, content=content, tokens=tokens))
            budget_left -= tokens
        return slices, truncated


def _task_to_payload(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "feature_ids": task.feature_ids,
        "allow_paths": task.allow_paths,
        "acceptance_criteria": task.acceptance_criteria,
        "verify_command": task.verify_command,
        "priority": task.priority,
        "depends_on": list(task.depends_on),
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "block_reason": task.block_reason,
    }


def _fit_text(text: str, remaining: int) -> tuple[str, int, bool]:
    if not text:
        return "", remaining, False
    if remaining <= 0:
        return "", remaining, True
    fitted: str = truncate_to_tokens(text, max_tokens=remaining)
    used: int = estimate_tokens(fitted)
    return fitted, remaining - used, len(fitted) < len(text)


def _read_agent_text(path: Path, *, max_chars: int) -> str:
    if not path.is_file():
        return ""
    try:
        text: str = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n…(truncated)"
    return text


def _load_feature_context(agent_root: Path, feature_ids: str) -> str:
    if not feature_ids.strip():
        return ""
    chunks: list[str] = []
    for feature_id in [part.strip() for part in feature_ids.split(",") if part.strip()]:
        path: Path = agent_root / "features" / feature_id / "context.md"
        text: str = _read_agent_text(path, max_chars=MAX_FEATURE_CHARS)
        if text:
            chunks.append(f"### feature `{feature_id}`\n\n{text}")
        else:
            chunks.append(
                f"### feature `{feature_id}`\n\n_(no `.agent/features/{feature_id}/context.md`)_"
            )
    return "\n\n".join(chunks)


def _search_query_from_task(task: Task) -> str:
    parts: list[str] = []
    if task.feature_ids:
        parts.extend(part.strip() for part in task.feature_ids.split(",") if part.strip())
    for token in task.title.replace(":", " ").replace("/", " ").split():
        cleaned: str = "".join(ch for ch in token if ch.isalnum() or ch in "-_")
        if len(cleaned) >= 3:
            parts.append(cleaned)
    # Prefer first meaningful token; rg uses fixed-string via -F in helper.
    for part in parts:
        if part.lower() not in {"demo", "task", "the", "and", "for"}:
            return part
    return parts[0] if parts else ""


def _rg_files(*, project_root: Path, query: str, limit: int) -> list[Path]:
    command: list[str] = [
        "rg",
        "-l",
        "-F",
        "--glob",
        "!node_modules/**",
        "--glob",
        "!.git/**",
        "--glob",
        "!.agent/**",
        "--glob",
        "!dist/**",
        "--glob",
        "!build/**",
        query,
        str(project_root),
    ]
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=RG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode not in (0, 1):
        return []
    paths: list[Path] = []
    for line in completed.stdout.splitlines():
        candidate: Path = Path(line.strip())
        if candidate.is_file():
            paths.append(candidate)
        if len(paths) >= limit:
            break
    return paths


def _read_file_head(path: Path, *, max_chars: int) -> str:
    try:
        text: str = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n…(truncated)"
    return text
