"""Turn verifier evidence into the next prompt, and reject syntax errors early."""

from __future__ import annotations

from pathlib import Path

FAILURE_SUMMARY_LIMIT: int = 1600
SOURCE_SNAPSHOT_LIMIT: int = 1800


def summarize_test_failure(stdout: str, stderr: str, *, limit: int = FAILURE_SUMMARY_LIMIT) -> str:
    """Keep the traceback and assertion text, not the leading progress noise."""
    parts: list[str] = []
    if stdout.strip():
        parts.append(stdout.strip())
    if stderr.strip():
        parts.append(stderr.strip())
    text: str = "\n".join(parts)
    if not text:
        return "no test output"
    marker: int = text.rfind("Traceback (most recent call last):")
    if marker >= 0:
        return _clip(text[marker:], limit)
    interesting: list[str] = [
        line.rstrip()
        for line in text.splitlines()
        if _is_failure_line(line)
    ]
    if interesting:
        return _clip("\n".join(interesting), limit)
    return _clip(text[-limit:], limit)


def snapshot_sources(project_root: Path, *, limit: int = SOURCE_SNAPSHOT_LIMIT) -> str:
    """Return the src files that were on disk for this attempt."""
    source_root: Path = project_root / "src"
    if not source_root.is_dir():
        return ""
    chunks: list[str] = []
    used: int = 0
    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            content: str = path.read_text(encoding="utf-8")
        except OSError:
            continue
        relative: str = path.relative_to(project_root).as_posix()
        block: str = f"### {relative}\n```\n{content.rstrip()}\n```"
        if used + len(block) > limit:
            remaining: int = limit - used
            if remaining > 80:
                chunks.append(block[:remaining].rstrip() + "\n…(truncated)")
            break
        chunks.append(block)
        used += len(block)
    if not chunks:
        return ""
    return "## src that was tested\n" + "\n".join(chunks)


def compile_sources(project_root: Path) -> str:
    """Return a SyntaxError summary for src/**/*.py, or an empty string."""
    source_root: Path = project_root / "src"
    if not source_root.is_dir():
        return ""
    errors: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative: str = path.relative_to(project_root).as_posix()
        try:
            source: str = path.read_text(encoding="utf-8")
        except OSError as err:
            errors.append(f"SyntaxError: {relative}: {err}")
            continue
        try:
            compile(source, relative, "exec")
        except SyntaxError as err:
            errors.append(f"SyntaxError: {relative}:{err.lineno}: {err.msg}")
    return "\n".join(errors)


def _is_failure_line(line: str) -> bool:
    stripped: str = line.strip()
    if stripped.startswith(("FAIL:", "ERROR:", "AssertionError", "Traceback", "File ", "assert ")):
        return True
    if "Error:" in stripped or "Exception:" in stripped:
        return True
    return "!=" in stripped or stripped.startswith(("FAILED", "Ran "))


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 20)].rstrip() + "\n…(truncated)"
