"""Phase 1 Project Analyzer: read-only scan → fill ``.agent/`` (no source edits)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roop.harness.fs_guard import WriteGuard

STACK_MARKERS: dict[str, str] = {
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "package.json": "node",
    "pubspec.yaml": "dart/flutter",
    "Cargo.toml": "rust",
    "go.mod": "go",
}

INTERESTING_TOP_DIRS: tuple[str, ...] = (
    "src",
    "app",
    "apps",
    "lib",
    "ios",
    "android",
    "web",
    "supabase",
    "docs",
    "scripts",
    "tests",
    "test",
    "__tests__",
)

KEY_NODE_DEPS: tuple[str, ...] = (
    "react",
    "react-native",
    "typescript",
    "@supabase/supabase-js",
    "@react-navigation/native",
    "react-native-iap",
    "expo",
    "next",
    "express",
)

MAX_AGENTS_CHARS: int = 4000
MAX_README_CHARS: int = 2000


@dataclass(frozen=True, slots=True)
class ProjectFacts:
    """Deterministic facts collected from the target tree."""

    target_root: Path
    detected_stacks: list[str]
    package_name: str | None = None
    package_version: str | None = None
    package_description: str | None = None
    dependencies: dict[str, str] = field(default_factory=dict)
    scripts: dict[str, str] = field(default_factory=dict)
    top_dirs: list[str] = field(default_factory=list)
    src_children: list[str] = field(default_factory=list)
    edge_functions: list[str] = field(default_factory=list)
    has_agents_md: bool = False
    has_supabase: bool = False
    has_typescript: bool = False
    agents_excerpt: str = ""
    readme_excerpt: str = ""


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    """Result of a Phase 1 analyze pass."""

    target_root: Path
    agent_root: Path
    detected_stacks: list[str]
    created_files: list[str]
    facts: ProjectFacts


def execute_analyze(target_path: Path) -> AnalyzeResult:
    target_root: Path = target_path.resolve()
    if not target_root.exists():
        raise FileNotFoundError(f"Target path does not exist: {target_root}")
    if not target_root.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {target_root}")
    facts: ProjectFacts = collect_project_facts(target_root)
    guard: WriteGuard = WriteGuard(target_root)
    created_files: list[str] = write_agent_documents(guard=guard, facts=facts)
    return AnalyzeResult(
        target_root=target_root,
        agent_root=guard.agent_root,
        detected_stacks=facts.detected_stacks,
        created_files=created_files,
        facts=facts,
    )


def collect_project_facts(target_root: Path) -> ProjectFacts:
    detected: list[str] = _detect_stacks(target_root)
    package: dict[str, Any] = _load_package_json(target_root)
    dependencies: dict[str, str] = _string_map(package.get("dependencies"))
    dev_dependencies: dict[str, str] = _string_map(package.get("devDependencies"))
    merged_deps: dict[str, str] = {**dependencies, **dev_dependencies}
    scripts: dict[str, str] = _string_map(package.get("scripts"))
    if "react-native" in merged_deps and "react-native" not in detected:
        detected.append("react-native")
    if (target_root / "supabase").is_dir() and "supabase" not in detected:
        detected.append("supabase")
    has_typescript: bool = (
        "typescript" in merged_deps
        or (target_root / "tsconfig.json").exists()
        or any(path.suffix == ".ts" for path in (target_root / "src").glob("*.ts"))
        if (target_root / "src").is_dir()
        else "typescript" in merged_deps or (target_root / "tsconfig.json").exists()
    )
    if has_typescript and "typescript" not in detected:
        detected.append("typescript")
    agents_path: Path = target_root / "AGENTS.md"
    readme_path: Path = _find_readme(target_root)
    return ProjectFacts(
        target_root=target_root,
        detected_stacks=detected,
        package_name=_as_str(package.get("name")),
        package_version=_as_str(package.get("version")),
        package_description=_as_str(package.get("description")),
        dependencies=merged_deps,
        scripts=scripts,
        top_dirs=_list_interesting_dirs(target_root),
        src_children=_list_dir_names(target_root / "src"),
        edge_functions=_list_edge_functions(target_root),
        has_agents_md=agents_path.is_file(),
        has_supabase=(target_root / "supabase").is_dir(),
        has_typescript=has_typescript,
        agents_excerpt=_read_excerpt(agents_path, MAX_AGENTS_CHARS),
        readme_excerpt=_read_excerpt(readme_path, MAX_README_CHARS) if readme_path else "",
    )


def write_agent_documents(*, guard: WriteGuard, facts: ProjectFacts) -> list[str]:
    documents: dict[str, str] = {
        "AGENTS.md": _render_agents_md(facts),
        "project/overview.md": _render_overview(facts),
        "project/tech-stack.md": _render_tech_stack(facts),
        "project/conventions.md": _render_conventions(facts),
        "project/structure.md": _render_structure(facts),
        "project/scripts.md": _render_scripts(facts),
        "state/current-state.md": _render_current_state(facts),
        "logs/.gitkeep": "",
    }
    created: list[str] = []
    for relative, content in documents.items():
        agent_relative: Path = Path(guard.AGENT_DIR_NAME) / relative
        written: Path = guard.write_text(agent_relative, content)
        created.append(str(written.relative_to(guard.agent_root)))
    return created


def _detect_stacks(target_root: Path) -> list[str]:
    found: list[str] = []
    for marker, stack_name in STACK_MARKERS.items():
        if (target_root / marker).exists() and stack_name not in found:
            found.append(stack_name)
    return found


def _load_package_json(target_root: Path) -> dict[str, Any]:
    path: Path = target_root / "package.json"
    if not path.is_file():
        return {}
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, raw in value.items():
        if isinstance(key, str) and isinstance(raw, str):
            result[key] = raw
    return result


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _list_interesting_dirs(target_root: Path) -> list[str]:
    names: list[str] = []
    for name in INTERESTING_TOP_DIRS:
        if (target_root / name).is_dir():
            names.append(name)
    return names


def _list_dir_names(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(
        child.name
        for child in path.iterdir()
        if child.is_dir() and not child.name.startswith(".")
    )


def _list_edge_functions(target_root: Path) -> list[str]:
    functions_root: Path = target_root / "supabase" / "functions"
    if not functions_root.is_dir():
        return []
    return sorted(
        child.name
        for child in functions_root.iterdir()
        if child.is_dir() and not child.name.startswith("_") and not child.name.startswith(".")
    )


def _find_readme(target_root: Path) -> Path | None:
    for name in ("README.md", "Readme.md", "readme.md"):
        candidate: Path = target_root / name
        if candidate.is_file():
            return candidate
    return None


def _read_excerpt(path: Path, limit: int) -> str:
    if not path.is_file():
        return ""
    try:
        text: str = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n…(truncated)"


def _render_agents_md(facts: ProjectFacts) -> str:
    return (
        "# AGENTS\n\n"
        "Roop Phase 1 project map. Writes are limited to `.agent/**`.\n\n"
        "Start with:\n"
        "- `project/overview.md`\n"
        "- `project/tech-stack.md`\n"
        "- `project/structure.md`\n"
        "- `project/conventions.md`\n"
        "- `state/current-state.md`\n"
    )


def _render_overview(facts: ProjectFacts) -> str:
    stacks: str = ", ".join(facts.detected_stacks) if facts.detected_stacks else "unknown"
    lines: list[str] = [
        "# Project overview",
        "",
        f"- Root: `{facts.target_root}`",
        f"- Detected stacks: {stacks}",
    ]
    if facts.package_name:
        lines.append(f"- Package: `{facts.package_name}`")
    if facts.package_version:
        lines.append(f"- Version: `{facts.package_version}`")
    if facts.package_description:
        lines.append(f"- Description: {facts.package_description}")
    if facts.has_agents_md:
        lines.append("- Guide: `AGENTS.md` present (see conventions)")
    if facts.has_supabase:
        lines.append(f"- Supabase Edge Functions: {len(facts.edge_functions)}")
    lines.append("")
    if facts.agents_excerpt:
        summary: str = _first_bullets(facts.agents_excerpt, limit=10)
        if summary:
            lines.extend(["## From AGENTS.md", "", summary, ""])
        else:
            lines.extend(["## From AGENTS.md", "", facts.agents_excerpt[:1200], ""])
    elif facts.readme_excerpt:
        lines.extend(["## README excerpt", "", facts.readme_excerpt, ""])
    return "\n".join(lines).rstrip() + "\n"


def _render_tech_stack(facts: ProjectFacts) -> str:
    lines: list[str] = [
        "# Tech stack",
        "",
        f"Detected: {', '.join(facts.detected_stacks) or 'unknown'}",
        "",
    ]
    if facts.dependencies:
        lines.append("## Key dependencies")
        lines.append("")
        for name in KEY_NODE_DEPS:
            version: str | None = facts.dependencies.get(name)
            if version:
                lines.append(f"- `{name}`: `{version}`")
        lines.append("")
    if facts.has_typescript:
        lines.append("- TypeScript: yes")
        lines.append("")
    if facts.edge_functions:
        lines.append("## Supabase Edge Functions")
        lines.append("")
        for name in facts.edge_functions:
            lines.append(f"- `{name}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_conventions(facts: ProjectFacts) -> str:
    if facts.agents_excerpt:
        return (
            "# Conventions\n\n"
            "Source: root `AGENTS.md` (excerpt).\n\n"
            f"{facts.agents_excerpt}\n"
        )
    return (
        "# Conventions\n\n"
        "No `AGENTS.md` found. Prefer existing project style; keep edits scoped.\n"
    )


def _render_structure(facts: ProjectFacts) -> str:
    lines: list[str] = ["# Structure", "", "## Top-level", ""]
    if facts.top_dirs:
        for name in facts.top_dirs:
            lines.append(f"- `{name}/`")
    else:
        lines.append("- (no standard app folders detected)")
    lines.append("")
    if facts.src_children:
        lines.extend(["## `src/`", ""])
        for name in facts.src_children:
            lines.append(f"- `src/{name}/`")
        lines.append("")
    if facts.edge_functions:
        lines.extend(["## `supabase/functions/`", ""])
        for name in facts.edge_functions:
            lines.append(f"- `supabase/functions/{name}/`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_scripts(facts: ProjectFacts) -> str:
    lines: list[str] = ["# Scripts", ""]
    if not facts.scripts:
        lines.append("No `package.json` scripts found.")
        lines.append("")
        return "\n".join(lines)
    lines.append("From `package.json`:")
    lines.append("")
    for name, command in sorted(facts.scripts.items()):
        lines.append(f"- `npm run {name}` → `{command}`")
    lines.append("")
    return "\n".join(lines)


def _render_current_state(facts: ProjectFacts) -> str:
    stacks: str = ", ".join(facts.detected_stacks) if facts.detected_stacks else "unknown"
    return (
        "# Current state\n\n"
        "Status: analyzed (phase 1)\n\n"
        f"- Stacks: {stacks}\n"
        f"- Package: {facts.package_name or 'n/a'}@{facts.package_version or 'n/a'}\n"
        f"- Top dirs: {', '.join(facts.top_dirs) or 'n/a'}\n"
        f"- Edge functions: {len(facts.edge_functions)}\n"
        "- Write scope: `.agent/**` only\n"
    )


def _first_bullets(markdown: str, *, limit: int) -> str:
    bullets: list[str] = []
    for line in markdown.splitlines():
        stripped: str = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped)
        if len(bullets) >= limit:
            break
    return "\n".join(bullets)
