"""Assemble narrow role packets from Task + ``.agent/`` docs (Phase 3)."""

from __future__ import annotations

import fnmatch
import json
import os
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
MAX_SLICES: int = 8
MAX_FEEDBACK_CHARS: int = 1200
MAX_PROJECT_CONTEXT_CHARS: int = 6000
MAX_PROJECT_FILE_CHARS: int = 2400
RG_TIMEOUT_SECONDS: float = 5.0

EXCLUDED_DIRS: frozenset[str] = frozenset({
    ".git", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".agent", "dist", "build", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".next", ".nuxt", "vendor",
})


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
    project_context: str
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
                "## Project context",
                self.project_context or "_(none)_",
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

        project_context: str = _collect_project_context(self._project_root)
        project_context, remaining, hit = _fit_text(project_context, remaining)
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
            project_context=project_context,
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

        hits: list[Path] = []
        for raw_pattern in task.allow_paths.split(","):
            pattern = raw_pattern.strip()
            if not pattern:
                continue

            if any(char in pattern for char in "*?["):
                hits.extend(_glob_files(self._project_root, pattern))
                continue

            candidate = (self._project_root / pattern).resolve()
            try:
                relative = candidate.relative_to(self._project_root)
            except ValueError:
                continue

            if (
                candidate.is_file()
                and not any(part in EXCLUDED_DIRS for part in relative.parts[:-1])
            ):
                hits.append(candidate)

        query: str = _search_query_from_task(task)
        if query:
            hits.extend(
                _rg_files(
                    project_root=self._project_root,
                    query=query,
                    limit=MAX_SLICES,
                )
            )

        unique_hits: list[Path] = []
        seen: set[Path] = set()
        for path in hits:
            resolved = path.resolve()
            if resolved in seen or not resolved.is_file():
                continue
            try:
                relative = resolved.relative_to(self._project_root)
            except ValueError:
                continue
            if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
                continue
            seen.add(resolved)
            unique_hits.append(resolved)
            if len(unique_hits) >= MAX_SLICES:
                break

        slices: list[CodeSlice] = []
        budget_left: int = remaining_tokens
        truncated: bool = False
        per_slice: int = max(200, remaining_tokens // max(1, MAX_SLICES))
        for path in unique_hits:
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


def _glob_files(project_root: Path, pattern: str) -> list[Path]:
    """Expand an allow-path glob while pruning excluded directories."""
    matches: list[Path] = []
    for current, dirs, files in os.walk(project_root):
        dirs[:] = sorted(
            name for name in dirs
            if name not in EXCLUDED_DIRS
        )
        current_path = Path(current)
        for name in sorted(files):
            candidate = current_path / name
            relative = candidate.relative_to(project_root).as_posix()
            if fnmatch.fnmatchcase(relative, pattern):
                matches.append(candidate)
    return matches


def _collect_project_context(project_root: Path) -> str:
    """Collect a bounded overview of project metadata and directory structure."""
    preferred_names = {
        "readme.md",
        "readme",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "pipfile",
        "package.json",
        "tsconfig.json",
        "jsconfig.json",
        "cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "composer.json",
        "gemfile",
        "mix.exs",
        "dockerfile",
        "docker-compose.yml",
        "compose.yml",
        "makefile",
    }
    excluded_dirs = EXCLUDED_DIRS

    candidates: list[Path] = []
    for path in project_root.iterdir():
        if not path.is_file():
            continue
        name = path.name.lower()
        if name in preferred_names or (
            name.startswith("requirements") and name.endswith(".txt")
        ):
            candidates.append(path)

    chunks: list[str] = []
    total_chars = 0
    for path in sorted(candidates, key=lambda item: item.name.lower()):
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not content:
            continue
        # Keep dependency lists tiny so models do not derail into unrelated stack work.
        if path.name.lower().startswith("requirements") and path.suffix == ".txt":
            lines = [line for line in content.splitlines() if line.strip()]
            preview = "\n".join(lines[:12])
            content = (
                f"{len(lines)} packages listed. Ignore unless the task needs deps.\n"
                f"{preview}"
            )
            if len(lines) > 12:
                content += "\n…"
        content = content[:MAX_PROJECT_FILE_CHARS]
        chunk = f"### {path.name}\n{content}"
        available = MAX_PROJECT_CONTEXT_CHARS - total_chars
        if available <= 0:
            break
        if len(chunk) > available:
            chunk = chunk[:available]
        chunks.append(chunk)
        total_chars += len(chunk)

    tree_lines: list[str] = []
    for current, dirs, files in os.walk(project_root):
        current_path = Path(current)
        depth = len(current_path.relative_to(project_root).parts)
        dirs[:] = sorted(
            name for name in dirs
            if name not in excluded_dirs and not name.startswith(".")
        )
        if depth >= 2:
            dirs[:] = []
        for name in sorted(dirs):
            relative = (current_path / name).relative_to(project_root)
            tree_lines.append(f"{relative}/")
        for name in sorted(files):
            if name.startswith(".") or name.endswith((".pyc", ".db", ".sqlite3")):
                continue
            relative = (current_path / name).relative_to(project_root)
            tree_lines.append(str(relative))
        if len(tree_lines) >= 80:
            tree_lines = tree_lines[:80]
            break

    if tree_lines and total_chars < MAX_PROJECT_CONTEXT_CHARS:
        tree = "### Directory structure\n" + "\n".join(tree_lines)
        available = MAX_PROJECT_CONTEXT_CHARS - total_chars
        chunks.append(tree[:available])

    return "\n\n".join(chunks)[:MAX_PROJECT_CONTEXT_CHARS]


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
    ignored = {
        "demo", "task", "the", "and", "for", "with",
        "from", "into", "this", "that", "add", "update",
        "implement", "support", "구현", "추가", "수정",
        "지원", "작업", "기능",
    }

    sources = [task.title, task.description or ""]

    if task.feature_ids:
        sources.append(task.feature_ids)

    for source in sources:
        normalized = (
            source.replace(":", " ")
            .replace("/", " ")
            .replace(",", " ")
            .replace(".", " ")
            .replace("(", " ")
            .replace(")", " ")
        )

        for token in normalized.split():
            cleaned = "".join(
                ch for ch in token
                if ch.isalnum() or ch in "-_"
            )

            if len(cleaned) < 3 or cleaned.lower() in ignored:
                continue

            if cleaned not in parts:
                parts.append(cleaned)

            if len(parts) >= 5:
                return "|".join(parts)

    return "|".join(parts)


def _rg_files(*, project_root: Path, query: str, limit: int) -> list[Path]:
    queries = [item.strip() for item in query.split("|") if item.strip()]
    if not queries or limit <= 0:
        return []

    command: list[str] = [
        "rg",
        "-l",
        "-F",
        "--glob", "!node_modules/**",
        "--glob", "!.git/**",
        "--glob", "!.agent/**",
        "--glob", "!dist/**",
        "--glob", "!build/**",
        "--glob", "!vendor/**",
        "--glob", "!.ruff_cache/**",
        "--glob", "!.mypy_cache/**",
        "--glob", "!.pytest_cache/**",
        "--glob", "!coverage/**",
        "--glob", "!__pycache__/**",
        "--glob", "!venv/**",
        "--glob", "!.venv/**",
    ]

    for item in queries:
        command.extend(["-e", item])

    command.append(str(project_root))

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
        candidate = Path(line)
        if not candidate.is_absolute():
            candidate = project_root / candidate

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
