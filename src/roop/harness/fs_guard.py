"""Filesystem write guard — Phase 0 default: only <target>/.agent/**."""

from __future__ import annotations

from pathlib import Path


class WriteGuardError(PermissionError):
    """Raised when a write path falls outside the allow list."""


class WriteGuard:
    """Allow writes only under ``<target>/.agent/**`` by default."""

    AGENT_DIR_NAME: str = ".agent"

    def __init__(self, target_root: Path, *, allow_agent_only: bool = True) -> None:
        self._target_root: Path = target_root.resolve()
        self._allow_agent_only: bool = allow_agent_only
        self._agent_root: Path = self._target_root / self.AGENT_DIR_NAME

    @property
    def target_root(self) -> Path:
        return self._target_root

    @property
    def agent_root(self) -> Path:
        return self._agent_root

    def is_write_allowed(self, path: Path) -> bool:
        resolved: Path = self._resolve_under_target(path)
        if not self._allow_agent_only:
            return self._is_relative_to(resolved, self._target_root)
        return self._is_relative_to(resolved, self._agent_root)

    def assert_write_allowed(self, path: Path) -> Path:
        resolved: Path = self._resolve_under_target(path)
        if not self.is_write_allowed(resolved):
            raise WriteGuardError(
                f"Write blocked outside {self._agent_root}: {resolved}"
            )
        return resolved

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> Path:
        resolved: Path = self.assert_write_allowed(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding=encoding)
        return resolved

    def _resolve_under_target(self, path: Path) -> Path:
        candidate: Path = path if path.is_absolute() else self._target_root / path
        resolved: Path = candidate.resolve()
        if not self._is_relative_to(resolved, self._target_root):
            raise WriteGuardError(f"Path escapes target root: {resolved}")
        return resolved

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
