"""Filesystem write guard with allow_paths support (Phase 4+)."""

from __future__ import annotations

import fnmatch
from pathlib import Path


class WriteGuardError(PermissionError):
    """Raised when a write path falls outside the allow list."""


class WriteGuard:
    """Allow writes under ``.agent/**`` and optional ``allow_paths`` globs."""

    AGENT_DIR_NAME: str = ".agent"

    def __init__(
        self,
        target_root: Path,
        *,
        allow_agent_only: bool = True,
        allow_paths: list[str] | None = None,
    ) -> None:
        self._target_root: Path = target_root.resolve()
        self._allow_agent_only: bool = allow_agent_only
        self._agent_root: Path = self._target_root / self.AGENT_DIR_NAME
        self._allow_paths: list[str] = list(allow_paths or [])

    @property
    def target_root(self) -> Path:
        return self._target_root

    @property
    def agent_root(self) -> Path:
        return self._agent_root

    def with_allow_paths(self, allow_paths: list[str] | str) -> WriteGuard:
        patterns: list[str] = (
            split_allow_paths(allow_paths)
            if isinstance(allow_paths, str)
            else list(allow_paths)
        )
        return WriteGuard(
            self._target_root,
            allow_agent_only=self._allow_agent_only,
            allow_paths=patterns,
        )

    def is_write_allowed(self, path: Path | str) -> bool:
        resolved: Path = self._resolve_under_target(path)
        if self._is_relative_to(resolved, self._agent_root):
            return True
        if not self._allow_agent_only and self._is_relative_to(
            resolved, self._target_root
        ):
            return True
        relative: str = str(resolved.relative_to(self._target_root))
        return any(match_allow_path(relative, pattern) for pattern in self._allow_paths)

    def assert_write_allowed(self, path: Path | str) -> Path:
        resolved: Path = self._resolve_under_target(path)
        if not self.is_write_allowed(resolved):
            raise WriteGuardError(
                f"Write blocked outside allow list "
                f"(.agent/** + {self._allow_paths}): {resolved}"
            )
        return resolved

    def write_text(
        self,
        path: Path | str,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        resolved: Path = self.assert_write_allowed(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding=encoding)
        return resolved

    def _resolve_under_target(self, path: Path | str) -> Path:
        path_obj: Path = Path(path)
        candidate: Path = (
            path_obj if path_obj.is_absolute() else self._target_root / path_obj
        )
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


def split_allow_paths(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in raw.replace(";", ",").split(","):
        cleaned: str = chunk.strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def match_allow_path(relative: str, pattern: str) -> bool:
    normalized: str = relative.replace("\\", "/")
    normalized_pattern: str = pattern.replace("\\", "/").lstrip("./")
    if normalized_pattern.endswith("/**"):
        prefix: str = normalized_pattern[:-3]
        return normalized == prefix or normalized.startswith(prefix + "/")
    if "**" in normalized_pattern:
        return fnmatch.fnmatch(normalized, normalized_pattern)
    if normalized_pattern.endswith("/"):
        return (
            normalized.startswith(normalized_pattern)
            or normalized == normalized_pattern[:-1]
        )
    return fnmatch.fnmatch(normalized, normalized_pattern) or normalized == normalized_pattern
