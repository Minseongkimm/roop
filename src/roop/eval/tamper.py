"""Detect test-file tampering used to fake GREEN results."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from roop.harness.fs_guard import match_allow_path


@dataclass(frozen=True, slots=True)
class TamperResult:
    ok: bool
    detail: str
    changed_paths: tuple[str, ...] = ()


class TamperGuard:
    """Snapshot protected globs before a run and compare afterwards."""

    def __init__(self, project_root: Path, protected_globs: tuple[str, ...]) -> None:
        self._project_root: Path = project_root.resolve()
        self._protected_globs: tuple[str, ...] = protected_globs
        self._baseline: dict[str, str] = {}

    def snapshot(self) -> None:
        self._baseline = self._hash_protected()

    def check(self) -> TamperResult:
        current: dict[str, str] = self._hash_protected()
        changed: list[str] = []
        for path, digest in current.items():
            if path not in self._baseline:
                # New protected test files created by the agent are expected for greenfield
                # tasks; only flag modification of pre-existing protected files.
                continue
            if self._baseline[path] != digest:
                changed.append(path)
        for path in self._baseline:
            if path not in current:
                changed.append(path)
        if changed:
            return TamperResult(
                ok=False,
                detail="protected test files were modified or deleted",
                changed_paths=tuple(sorted(changed)),
            )
        return TamperResult(ok=True, detail="ok", changed_paths=())

    def _hash_protected(self) -> dict[str, str]:
        if not self._protected_globs:
            return {}
        found: dict[str, str] = {}
        for path in self._project_root.rglob("*"):
            if not path.is_file():
                continue
            relative: str = str(path.relative_to(self._project_root)).replace("\\", "/")
            if any(
                match_allow_path(relative, pattern) for pattern in self._protected_globs
            ):
                found[relative] = _sha256(path)
        return found


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
