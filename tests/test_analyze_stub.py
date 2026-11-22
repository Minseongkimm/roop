"""Tests for Phase 1 project analyzer."""

from __future__ import annotations

import json
from pathlib import Path

from roop.analyze.phase1 import AnalyzeResult, execute_analyze


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


def test_analyze_phase1_reads_react_native_project(tmp_path: Path) -> None:
    # Arrange
    input_root: Path = tmp_path / "rn-app"
    input_root.mkdir()
    package: dict[str, object] = {
        "name": "demo-app",
        "version": "1.2.3",
        "description": "demo rn",
        "scripts": {"start": "react-native start", "lint": "eslint ."},
        "dependencies": {
            "react": "19.1.0",
            "react-native": "0.80.2",
            "@supabase/supabase-js": "2.57.2",
        },
        "devDependencies": {"typescript": "5.8.3"},
    }
    (input_root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (input_root / "AGENTS.md").write_text("# Guide\n\n- Prefer Korean replies\n", encoding="utf-8")
    (input_root / "src").mkdir()
    (input_root / "src" / "screens").mkdir()
    (input_root / "supabase" / "functions" / "chat-stream").mkdir(parents=True)
    (input_root / "tsconfig.json").write_text("{}", encoding="utf-8")
    # Act
    actual: AnalyzeResult = execute_analyze(input_root)
    # Assert
    assert "node" in actual.detected_stacks
    assert "react-native" in actual.detected_stacks
    assert "supabase" in actual.detected_stacks
    assert "typescript" in actual.detected_stacks
    assert actual.facts.package_name == "demo-app"
    assert "chat-stream" in actual.facts.edge_functions
    structure: str = (actual.agent_root / "project" / "structure.md").read_text(encoding="utf-8")
    assert "src/screens/" in structure
    tech: str = (actual.agent_root / "project" / "tech-stack.md").read_text(encoding="utf-8")
    assert "react-native" in tech
    conventions: str = (actual.agent_root / "project" / "conventions.md").read_text(encoding="utf-8")
    assert "Prefer Korean replies" in conventions
    state: str = (actual.agent_root / "state" / "current-state.md").read_text(encoding="utf-8")
    assert "phase 1" in state
