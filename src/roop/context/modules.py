"""Module map for the coder prompt: imports, tree, signatures, file text."""

from __future__ import annotations

import ast
import re
from pathlib import Path

MAX_MODULE_MAP_CHARS: int = 7000
MAX_FILE_CHARS: int = 3500

_FROM_IMPORT: re.Pattern[str] = re.compile(
    r"^\s*from\s+(src(?:\.[\w]+)*)\s+import\s+(.+)$",
    re.MULTILINE,
)
_PLAIN_IMPORT: re.Pattern[str] = re.compile(
    r"^\s*import\s+(src(?:\.[\w]+)*)\s*$",
    re.MULTILINE,
)
_VERIFY_TEST_FILE: re.Pattern[str] = re.compile(r"(?:^|\s)-p\s+(\S+)")


def build_module_map(project_root: Path, verify_command: str) -> str:
    """Describe the src modules the fixed test imports."""
    test_path: Path | None = _golden_test_path(project_root, verify_command)
    if test_path is None:
        return ""
    try:
        test_source: str = test_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    imports: list[tuple[str, list[str]]] = _imports_from_test(test_source)
    lines: list[str] = ["Expected import paths:"]
    if not imports:
        lines.append("- (no src import found in the fixed test)")
    for module, names in imports:
        relative: str = _module_to_path(module)
        target: Path = project_root / relative
        status: str = "exists" if target.is_file() else "MISSING — create this file"
        shown: str = ", ".join(names) if names else "(module import)"
        lines.append(f"- from {module} import {shown}")
        lines.append(f"  file: {relative} ({status})")
    lines.append("")
    lines.append("Source tree:")
    tree: list[str] = _source_tree(project_root)
    if tree:
        lines.extend(f"- {item}" for item in tree)
    else:
        lines.append("- (no src python files yet)")
    lines.append("")
    lines.append("Signatures:")
    signature_lines: list[str] = _signature_lines(project_root, imports)
    if signature_lines:
        lines.extend(signature_lines)
    else:
        lines.append("- (no signatures yet)")
    lines.append("")
    lines.append("Related source:")
    related: list[str] = _related_contents(project_root, imports)
    if related:
        lines.extend(related)
    else:
        lines.append("- (files above are missing; create them with the imported names)")
    text: str = "\n".join(lines).rstrip() + "\n"
    if len(text) <= MAX_MODULE_MAP_CHARS:
        return text
    return text[: MAX_MODULE_MAP_CHARS - 20].rstrip() + "\n…(truncated)\n"


def _golden_test_path(project_root: Path, verify_command: str) -> Path | None:
    match: re.Match[str] | None = _VERIFY_TEST_FILE.search(verify_command)
    if match is None:
        return None
    name: str = match.group(1).strip("'\"")
    relative: str = name if name.startswith("tests/") else f"tests/{Path(name).name}"
    path: Path = project_root / relative
    if not path.is_file():
        return None
    return path


def _imports_from_test(source: str) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for match in _FROM_IMPORT.finditer(source):
        module: str = match.group(1)
        names: list[str] = _import_names(match.group(2))
        found.append((module, names))
        seen.add(module)
    for match in _PLAIN_IMPORT.finditer(source):
        module = match.group(1)
        if module in seen:
            continue
        found.append((module, []))
        seen.add(module)
    return found


def _import_names(raw: str) -> list[str]:
    names: list[str] = []
    for part in raw.split(","):
        cleaned: str = part.strip().strip("()")
        if not cleaned or cleaned == "*":
            continue
        name: str = cleaned.split(" as ")[0].strip()
        if name:
            names.append(name)
    return names


def _module_to_path(module: str) -> str:
    return module.replace(".", "/") + ".py"


def _source_tree(project_root: Path) -> list[str]:
    source_root: Path = project_root / "src"
    if not source_root.is_dir():
        return []
    paths: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        paths.append(path.relative_to(project_root).as_posix())
    return paths


def _signature_lines(
    project_root: Path,
    imports: list[tuple[str, list[str]]],
) -> list[str]:
    lines: list[str] = []
    for module, _names in imports:
        relative: str = _module_to_path(module)
        path: Path = project_root / relative
        if not path.is_file():
            lines.append(f"- {relative}: missing")
            continue
        lines.append(f"- {relative}:")
        lines.extend(f"  {item}" for item in _signatures(path))
    return lines


def _signatures(path: Path) -> list[str]:
    try:
        tree: ast.AST = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return ["(syntax error; signatures unavailable)"]
    lines: list[str] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef):
            lines.append(_format_signature(node))
        elif isinstance(node, ast.ClassDef):
            lines.append(f"class {node.name}")
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    lines.append(f"  {_format_signature(child)}")
    if not lines:
        return ["(no top-level functions or classes)"]
    return lines


def _format_signature(node: ast.FunctionDef) -> str:
    args: list[str] = [arg.arg for arg in node.args.args]
    return f"def {node.name}({', '.join(args)})"


def _related_contents(
    project_root: Path,
    imports: list[tuple[str, list[str]]],
) -> list[str]:
    chunks: list[str] = []
    for module, _names in imports:
        relative: str = _module_to_path(module)
        path: Path = project_root / relative
        if not path.is_file():
            continue
        try:
            content: str = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS].rstrip() + "\n…(truncated)"
        chunks.append(f"### {relative}\n```\n{content.rstrip()}\n```")
    return chunks
