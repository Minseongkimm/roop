"""Harness tools — only the orchestrator executes side effects (Phase 4)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from roop.harness.fs_guard import WriteGuard, WriteGuardError

DEFAULT_COMMAND_TIMEOUT: float = 120.0
RG_TIMEOUT_SECONDS: float = 8.0


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Outcome of a harness shell command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass(frozen=True, slots=True)
class PatchResult:
    """Outcome of applying a file write/patch."""

    path: str
    applied: bool
    detail: str


class ToolHarness:
    """Narrow tool surface: read, rg, write, run, git_diff."""

    def __init__(self, project_root: Path, guard: WriteGuard) -> None:
        self._project_root: Path = project_root.resolve()
        self._guard: WriteGuard = guard

    def read_file(self, relative_path: str, *, max_chars: int = 8000) -> str:
        path: Path = (self._project_root / relative_path).resolve()
        if not str(path).startswith(str(self._project_root)):
            raise WriteGuardError(f"Path escapes target root: {path}")
        if not path.is_file():
            return ""
        text: str = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars].rstrip() + "\n…(truncated)"
        return text

    def search(self, query: str, *, limit: int = 20) -> list[str]:
        command: list[str] = [
            "rg",
            "-n",
            "-F",
            "--glob",
            "!node_modules/**",
            "--glob",
            "!.git/**",
            "--glob",
            "!.agent/**",
            query,
            str(self._project_root),
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
        lines: list[str] = []
        for line in completed.stdout.splitlines():
            lines.append(line)
            if len(lines) >= limit:
                break
        return lines

    def write_file(self, relative_path: str, content: str) -> PatchResult:
        try:
            written: Path = self._guard.write_text(relative_path, content)
        except WriteGuardError as err:
            return PatchResult(path=relative_path, applied=False, detail=str(err))
        rel: str = str(written.relative_to(self._project_root))
        return PatchResult(path=rel, applied=True, detail="written")

    def path_exists(self, relative_path: str) -> bool:
        path = (self._project_root / relative_path).resolve()
        try:
            path.relative_to(self._project_root)
        except ValueError as err:
            raise WriteGuardError(f"Path escapes target root: {path}") from err
        return path.is_file()

    def apply_unified_hunk(
        self,
        relative_path: str,
        *,
        find: str,
        replace: str,
    ) -> PatchResult:
        if not find:
            return PatchResult(
                path=relative_path,
                applied=False,
                detail="empty find string is not allowed",
            )

        current: str = self.read_file(relative_path, max_chars=2_000_000)
        occurrences = current.count(find)

        if occurrences == 0:
            return PatchResult(
                path=relative_path,
                applied=False,
                detail="find string not present",
            )

        if occurrences > 1:
            return PatchResult(
                path=relative_path,
                applied=False,
                detail=f"find string is ambiguous: {occurrences} matches",
            )

        updated: str = current.replace(find, replace, 1)
        return self.write_file(relative_path, updated)

    def run_command(
        self,
        command: str,
        *,
        timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT,
    ) -> CommandResult:
        if not command.strip():
            return CommandResult(command=command, exit_code=1, stdout="", stderr="empty command")
        try:
            completed: subprocess.CompletedProcess[str] = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=self._project_root,
            )
        except subprocess.TimeoutExpired as err:
            return CommandResult(
                command=command,
                exit_code=124,
                stdout=err.stdout or "",
                stderr="timeout",
            )
        except OSError as err:
            return CommandResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=str(err),
            )
        return CommandResult(
            command=command,
            exit_code=int(completed.returncode),
            stdout=completed.stdout[-8000:],
            stderr=completed.stderr[-4000:],
        )

    def git_diff(self, *, max_chars: int = 8000) -> str:
        result: CommandResult = self.run_command("git diff --no-color")
        text: str = result.stdout or result.stderr
        if len(text) > max_chars:
            return text[:max_chars].rstrip() + "\n…(truncated)"
        return text



class FileTransaction:
    """Keep original file contents and roll back unverified writes."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()
        self._originals: dict[Path, bytes | None] = {}
        self._finished = False

    def capture(self, relative_path: str) -> None:
        if self._finished:
            raise RuntimeError("transaction already finished")

        path = (self._root / relative_path).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as err:
            raise WriteGuardError(f"Path escapes target root: {path}") from err

        if path not in self._originals:
            self._originals[path] = path.read_bytes() if path.is_file() else None

    def commit(self) -> None:
        self._finished = True
        self._originals.clear()

    def rollback(self) -> None:
        if self._finished:
            return

        for path, original in reversed(list(self._originals.items())):
            if original is None:
                if path.is_file():
                    path.unlink()
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original)

        self._finished = True
        self._originals.clear()
