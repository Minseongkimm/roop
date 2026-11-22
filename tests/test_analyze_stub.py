"""Tests for Phase 0 analyze scaffold."""

from __future__ import annotations

from pathlib import Path

from roop.analyze.stub import AnalyzeResult, execute_analyze


def test_analyze_creates_agent_tree_for_python_project(tmp_path: Path) -> None:
    # Arrange
    input_root: Path = tmp_path / "app"
    input_root.mkdir()
    (input_root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    # Act
    actual: AnalyzeResult = execute_analyze(input_root)
    # Assert
    assert "python" in actual.detected_stacks
    assert (actual.agent_root / "AGENTS.md").is_file()
    assert (actual.agent_root / "project" / "tech-stack.md").is_file()
    assert (actual.agent_root / "state" / "current-state.md").is_file()
    assert not (input_root / "src").exists()
