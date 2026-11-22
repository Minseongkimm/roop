"""Verifier — code/shell truth over model claims (Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from roop.executor.agent import ExecutionResult
from roop.harness.fs_guard import WriteGuard, match_allow_path, split_allow_paths
from roop.harness.tools import CommandResult, ToolHarness
from roop.orchestrator.tasks import Task


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """GREEN/RED decision with machine evidence."""

    green: bool
    expected: str
    saw: str
    exit_code: int | None = None
    details: list[str] = field(default_factory=list)

    def feedback(self) -> str:
        lines: list[str] = [
            f"EXPECTED: {self.expected}",
            f"SAW: {self.saw}",
            f"GREEN: {self.green}",
        ]
        lines.extend(self.details)
        hint: str = _repair_hint(self.saw)
        if hint:
            lines.append(f"ACTION: {hint}")
        return "\n".join(lines)


class Verifier:
    """Validate allow_paths + optional verify_command exit code."""

    def __init__(self, project_root: Path) -> None:
        self._project_root: Path = project_root.resolve()

    def verify(
        self,
        task: Task,
        execution: ExecutionResult,
        *,
        run_command: bool = True,
    ) -> VerifyResult:
        details: list[str] = []
        allow_patterns: list[str] = split_allow_paths(task.allow_paths) or [".agent/**"]
        # Always allow .agent writes
        for patch in execution.patches:
            if not patch.applied:
                details.append(f"patch failed: {patch.path} ({patch.detail})")
                return VerifyResult(
                    green=False,
                    expected="all patches applied inside allow_paths",
                    saw=patch.detail,
                    details=details,
                )
            if not _path_allowed(patch.path, allow_patterns):
                details.append(f"path outside allow_paths: {patch.path}")
                return VerifyResult(
                    green=False,
                    expected=f"paths within {allow_patterns}",
                    saw=patch.path,
                    details=details,
                )
        command_result: CommandResult | None = execution.command
        verify_command: str = task.verify_command.strip()
        if run_command and verify_command and command_result is None:
            guard: WriteGuard = WriteGuard(self._project_root).with_allow_paths(
                allow_patterns
            )
            tools: ToolHarness = ToolHarness(self._project_root, guard)
            command_result = tools.run_command(verify_command)
        if verify_command:
            if command_result is None:
                return VerifyResult(
                    green=False,
                    expected=f"verify_command exit 0: {verify_command}",
                    saw="command not run",
                    details=details,
                )
            if not command_result.ok:
                saw: str = (
                    command_result.stderr.strip()
                    or command_result.stdout.strip()
                    or f"exit {command_result.exit_code}"
                )
                details.append(f"command: {command_result.command}")
                return VerifyResult(
                    green=False,
                    expected=f"exit 0 from `{verify_command}`",
                    saw=saw[:500],
                    exit_code=command_result.exit_code,
                    details=details,
                )
            details.append(f"verify_command ok: {verify_command}")
        if execution.role.value == "coder" and not execution.patches:
            return VerifyResult(
                green=False,
                expected="at least one applied patch",
                saw="no patches",
                details=details,
            )
        if not execution.ok and execution.role.value in {"coder", "reviewer", "tester"}:
            return VerifyResult(
                green=False,
                expected="execution.ok",
                saw=execution.message,
                details=details,
            )
        return VerifyResult(
            green=True,
            expected="allow_paths + verify_command",
            saw="ok",
            exit_code=0 if command_result is None else command_result.exit_code,
            details=details,
        )


def _path_allowed(relative: str, patterns: list[str]) -> bool:
    normalized: str = relative.replace("\\", "/").lstrip("./")
    if normalized.startswith(".agent/") or normalized == ".agent":
        return True
    return any(match_allow_path(normalized, pattern) for pattern in patterns)


def _repair_hint(saw: str) -> str:
    text: str = saw.lower()
    if "failed to import" in text or "importerror" in text or "modulenotfounderror" in text:
        return (
            "Create BOTH implementation and test files with content. "
            "Every import in the test must resolve. "
            "Use real newlines in file bodies; keep Python string literals valid "
            "(no raw line breaks inside quotes)."
        )
    if "syntaxerror" in text:
        return (
            "Rewrite the file with valid Python. "
            "Do not put raw line breaks inside quoted strings; use \\n escapes in literals."
        )
    if "assertionerror" in text or "lists differ" in text or " != " in saw:
        return (
            "Fix the failing assertion or implementation to match acceptance_criteria. "
            "Do not invent unrelated apps or frameworks."
        )
    if "find string not present" in text:
        return "For new files use content, not find/replace against missing text."
    if "no tests ran" in text or "ran 0 tests" in text:
        return "Create the test module named by verify_command with content."
    if "empty find" in text:
        return "Use content for new files; find must be non-empty for edits."
    return ""
