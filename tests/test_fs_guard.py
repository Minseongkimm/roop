"""Tests for WriteGuard allow-list behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from roop.harness.fs_guard import WriteGuard, WriteGuardError


def test_allows_write_under_agent(tmp_path: Path) -> None:
    # Arrange
    input_target: Path = tmp_path / "project"
    input_target.mkdir()
    guard: WriteGuard = WriteGuard(input_target)
    expected_path: Path = input_target / ".agent" / "notes.md"
    # Act
    actual_path: Path = guard.write_text(Path(".agent/notes.md"), "hello")
    # Assert
    assert actual_path == expected_path
    assert expected_path.read_text(encoding="utf-8") == "hello"


def test_blocks_write_outside_agent(tmp_path: Path) -> None:
    # Arrange
    input_target: Path = tmp_path / "project"
    input_target.mkdir()
    guard: WriteGuard = WriteGuard(input_target)
    # Act / Assert
    with pytest.raises(WriteGuardError):
        guard.write_text(Path("src/main.py"), "nope")


def test_blocks_path_escape(tmp_path: Path) -> None:
    # Arrange
    input_target: Path = tmp_path / "project"
    input_target.mkdir()
    guard: WriteGuard = WriteGuard(input_target)
    # Act / Assert
    with pytest.raises(WriteGuardError):
        guard.assert_write_allowed(tmp_path / "outside.txt")


def test_is_write_allowed_for_nested_agent_file(tmp_path: Path) -> None:
    # Arrange
    input_target: Path = tmp_path / "project"
    input_target.mkdir()
    guard: WriteGuard = WriteGuard(input_target)
    input_path: Path = Path(".agent/project/overview.md")
    # Act
    actual: bool = guard.is_write_allowed(input_path)
    # Assert
    assert actual is True
