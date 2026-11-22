from __future__ import annotations

from pathlib import Path

import pytest

from roop.harness.fs_guard import WriteGuard


def test_allows_agent_writes(tmp_path: Path) -> None:
    guard: WriteGuard = WriteGuard(tmp_path)
    target: Path = tmp_path / ".agent" / "state" / "current-state.md"
    guard.write_text(target, "ok\n")
    assert target.read_text(encoding="utf-8") == "ok\n"


def test_blocks_source_writes(tmp_path: Path) -> None:
    guard: WriteGuard = WriteGuard(tmp_path)
    target: Path = tmp_path / "src" / "app.py"
    with pytest.raises(PermissionError):
        guard.write_text(target, "nope\n")
