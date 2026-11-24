"""Failure-aware retry loop. The harness, not the engine, decides pass or fail.

One task = up to ``max_local_attempts`` local generations, each graded by the
golden test. A failure is classified cheaply from the unittest output, and the
next prompt changes with the failure kind. When the same failure repeats, the
next attempt starts from a clean tree and is told to try a different approach.
After the local budget is spent, an optional escalation engine (API model) gets
the same history once.

Paths outside ``editable_files`` are reverted after every generation, so tests
stay read-only and a test edit can never count as a pass.
"""

from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from roop.engines.base import CodingEngine, EngineGeneration, EngineRequest
from roop.engines.harness import changed_locked_paths, restore_tree, snapshot_tree

MAX_LOCAL_ATTEMPTS: int = 3
RETRY_TEMPERATURES: tuple[float, ...] = (0.0, 0.2, 0.4)
MAX_SECONDS_PER_RETRY_TASK: float = 900.0
TEST_TIMEOUT_SECONDS: float = 60.0
_EXCERPT_CHARS: int = 1800

# kind -> (guessed cause, what the next prompt asks for)
FAILURE_GUIDE: dict[str, tuple[str, str]] = {
    "import": (
        "a module, file, or name the test imports does not exist",
        "Create every editable file and export exactly the names the test imports "
        "(check the import lines at the top of the test).",
    ),
    "syntax": (
        "the file does not parse",
        "Rewrite the whole file as valid Python. Check indentation, quotes and brackets.",
    ),
    "assertion": (
        "the code runs but returns a wrong value for some input",
        "Compare expected vs actual in the failing assertions below and fix the logic "
        "for those inputs, including edge cases (empty input, boundaries, ordering).",
    ),
    "exception": (
        "the wrong exception is raised, or an expected exception is not raised",
        "Re-read the spec for which inputs must raise which exception type, and "
        "validate inputs before doing the work.",
    ),
    "timeout": (
        "the code hangs or is too slow (likely an infinite loop)",
        "Remove any loop that may not terminate and avoid blocking calls.",
    ),
    "format": (
        "the engine did not produce a usable edit",
        "Return the complete content of every editable file.",
    ),
    "other": (
        "the tests failed for an unclassified reason",
        "Read the failing test output below carefully and fix the cause.",
    ),
}

EXCEPTION_CONTRACT: str = (
    "bool is not an int: bool is a subclass of int, so reject bool when the spec "
    "requires an int. Raise only the exception types named in the spec."
)
_FAILED_TEST_RE: re.Pattern[str] = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)", re.MULTILINE)
_AIDER_BANNER_RE: re.Pattern[str] = re.compile(
    r"^(?:>\s*)?(Detected dumb terminal\b|Aider v\d|Model:|Git repo:|Repo-map:|Added .+ to the chat\.)"
)
_UNEXPECTED_EXC_RE: re.Pattern[str] = re.compile(
    r"^(?!AssertionError)([A-Za-z_][\w.]*(?:Error|Exception)):", re.MULTILINE
)


@dataclass(frozen=True, slots=True)
class TestRun:
    passed: bool
    output: str
    timed_out: bool = False


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    index: int
    engine: str
    temperature: float
    passed: bool
    kind: str
    failing_tests: tuple[str, ...]
    changes: str
    cause: str
    excerpt: str
    locked_reverted: tuple[str, ...]
    fresh_start: bool
    elapsed_seconds: float
    unchanged_edit: bool = False

    def signature(self) -> tuple[str, tuple[str, ...]]:
        return (self.kind, self.failing_tests)


@dataclass(frozen=True, slots=True)
class RetryResult:
    first_pass: bool
    local_eventual: bool
    eventual: bool
    attempts_used: int
    local_attempts: int
    escalated: bool
    escalation_solved: bool
    attempts: tuple[AttemptRecord, ...]
    elapsed_seconds: float
    stop_reason: str
    kinds: tuple[str, ...] = field(default_factory=tuple)


def classify_test_failure(output: str, *, timed_out: bool = False) -> str:
    """Cheap failure kind from unittest/pytest output."""
    if timed_out:
        return "timeout"
    text: str = output or ""
    if "SyntaxError" in text or "IndentationError" in text:
        return "syntax"
    if (
        "ModuleNotFoundError" in text
        or "ImportError" in text
        or "cannot import name" in text
        or re.search(r"AttributeError: module '[^']+' has no attribute", text)
    ):
        return "import"
    if re.search(r"\bnot raised\b", text):
        return "exception"
    if _UNEXPECTED_EXC_RE.search(text) and "ERROR:" in text:
        return "exception"
    if "AssertionError" in text or "FAIL:" in text:
        return "assertion"
    if "timeout" in text.lower() or "TimeoutExpired" in text:
        return "timeout"
    return "other"


def failing_tests(output: str) -> tuple[str, ...]:
    return tuple(sorted({match.group(2) for match in _FAILED_TEST_RE.finditer(output or "")}))


def strip_aider_banner(text: str) -> str:
    """Drop Aider's startup banner so feedback is the test failure, not the CLI log."""
    kept: list[str] = []
    for line in (text or "").splitlines():
        if _AIDER_BANNER_RE.match(line.strip()):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def failure_excerpt(output: str, limit: int = _EXCERPT_CHARS) -> str:
    """Keep the unittest failure blocks; drop the passing ``... ok`` lines."""
    text: str = strip_aider_banner(output or "")
    start: int = text.find("=" * 20)
    if start >= 0:
        text = text[start:]
    else:
        text = "\n".join(line for line in text.splitlines() if not line.rstrip().endswith("... ok"))
    text = text.strip()
    if len(text) > limit:
        text = text[:limit] + "\n...[truncated]"
    return text


def summarize_changes(before: dict[str, bytes], after: dict[str, bytes], files: tuple[str, ...]) -> str:
    parts: list[str] = []
    for relative in files:
        old: list[str] = before.get(relative, b"").decode("utf-8", "replace").splitlines()
        new: list[str] = after.get(relative, b"").decode("utf-8", "replace").splitlines()
        if old == new:
            parts.append(f"{relative}: unchanged")
            continue
        added: int = 0
        removed: int = 0
        for line in difflib.ndiff(old, new):
            if line.startswith("+ "):
                added += 1
            elif line.startswith("- "):
                removed += 1
        parts.append(f"{relative}: +{added} -{removed}")
    return ", ".join(parts)


def run_test_command(workdir: Path, test_command: str, timeout: float = TEST_TIMEOUT_SECONDS) -> TestRun:
    """Run the golden test. Stale bytecode must never grade an older attempt:
    two same-size rewrites in the same second keep a valid-looking .pyc."""
    for cache in list(workdir.rglob("__pycache__")):
        shutil.rmtree(cache, ignore_errors=True)
    env: dict[str, str] = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            test_command,
            cwd=workdir,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return TestRun(passed=False, output="timeout", timed_out=True)
    return TestRun(
        passed=completed.returncode == 0,
        output=f"{completed.stderr}\n{completed.stdout}".strip(),
    )


def build_retry_prompt(
    base_prompt: str,
    history: list[AttemptRecord],
    *,
    fresh_start: bool,
    escalation: bool = False,
) -> str:
    """First attempt: the spec. Later attempts: spec + failure + attempt log + strategy."""
    if not history:
        return base_prompt
    last: AttemptRecord = history[-1]
    _, instruction = FAILURE_GUIDE.get(last.kind, FAILURE_GUIDE["other"])
    log_lines: list[str] = []
    for item in history:
        tests: str = ", ".join(item.failing_tests) or "-"
        start: str = " (fresh start)" if item.fresh_start else ""
        log_lines.append(
            f"- attempt {item.index + 1}{start}: changed {item.changes or '-'}; "
            f"failure={item.kind}; failing tests={tests}; likely cause: {item.cause}"
        )
    repeated: bool = len(history) >= 2 and history[-1].signature() == history[-2].signature()
    sections: list[str] = [
        "Original task (unchanged spec):",
        base_prompt.strip(),
        "",
        "Previous attempts did not pass the read-only tests. Attempt log:",
        *log_lines,
        "",
        f"Latest failure kind: {last.kind}. What to do: {instruction}",
        "",
        EXCEPTION_CONTRACT,
    ]
    if last.unchanged_edit:
        sections += [
            "",
            "The last edit left every editable file byte-for-byte unchanged. "
            "Do not repeat that code. Use a different approach.",
            "The failure below is the previous real test failure, not an edit-format error.",
        ]
    if fresh_start:
        sections += [
            "",
            "The previous code was discarded and the files were reset. "
            "Do NOT reproduce the approach from the log above; it failed the same way more than once. "
            "Re-read the spec and use a different implementation strategy.",
        ]
    elif repeated:
        sections += [
            "",
            "The same failure happened twice. Try a different approach instead of a small tweak.",
        ]
    else:
        sections += ["", "The current file content is your previous attempt. Fix it."]
    if escalation:
        sections += [
            "",
            "A smaller model could not solve this. Solve it fully and carefully.",
        ]
    sections += ["", "Failing test output:", last.excerpt or "(no output)"]
    return "\n".join(sections)


def run_retry_loop(
    engine: CodingEngine,
    *,
    prompt: str,
    editable_files: tuple[str, ...],
    test_command: str,
    workdir: Path,
    max_local_attempts: int = MAX_LOCAL_ATTEMPTS,
    temperatures: tuple[float, ...] = RETRY_TEMPERATURES,
    escalation_engine: CodingEngine | None = None,
    escalation_attempts: int = 1,
    max_seconds: float = MAX_SECONDS_PER_RETRY_TASK,
    clock: Callable[[], float] | None = None,
    grader: Callable[[Path, str], TestRun] | None = None,
    on_attempt: Callable[[AttemptRecord], None] | None = None,
) -> RetryResult:
    """Run local attempts with failure-aware prompts, then optional escalation."""
    now: Callable[[], float] = clock or time.monotonic
    grade: Callable[[Path, str], TestRun] = grader or run_test_command
    started: float = now()
    baseline: dict[str, bytes] = snapshot_tree(workdir)
    allowed: frozenset[str] = frozenset(path.replace("\\", "/").lstrip("./") for path in editable_files)
    history: list[AttemptRecord] = []
    stop_reason: str = "exhausted"
    local_attempts: int = 0
    escalated: bool = False
    escalation_solved: bool = False

    plan: list[tuple[CodingEngine, bool]] = [(engine, False)] * max(0, max_local_attempts)
    if escalation_engine is not None:
        plan += [(escalation_engine, True)] * max(0, escalation_attempts)

    for step, (current, is_escalation) in enumerate(plan):
        if history and history[-1].passed:
            break
        if is_escalation and not escalated:
            escalated = True
        elif now() - started >= max_seconds:
            stop_reason = "time_cap"
            break
        repeated: bool = len(history) >= 2 and history[-1].signature() == history[-2].signature()
        fresh: bool = is_escalation or repeated
        if fresh or not history:
            restore_tree(workdir, baseline)
        request_prompt: str = build_retry_prompt(
            prompt, history, fresh_start=fresh and bool(history), escalation=is_escalation
        )
        temperature: float = 0.0 if is_escalation else temperatures[min(step, len(temperatures) - 1)]
        before: dict[str, bytes] = snapshot_tree(workdir)
        attempt_started: float = now()
        request: EngineRequest = EngineRequest(
            prompt=request_prompt,
            editable_files=editable_files,
            test_command=test_command,
            workdir=workdir,
            temperature=temperature,
        )
        try:
            generation: EngineGeneration = current.generate(request)
        except Exception as exc:  # engine crash = format failure, keep going
            generation = EngineGeneration(format_ok=False, format_error=f"{type(exc).__name__}: {exc}")
        locked: tuple[str, ...] = changed_locked_paths(workdir, baseline, allowed)
        if locked:
            _revert_paths(workdir, baseline, locked)
        after: dict[str, bytes] = snapshot_tree(workdir)
        files_changed: bool = _changed(before, after, editable_files)
        unchanged_edit: bool = _is_unchanged_edit(generation, files_changed=files_changed)
        if not generation.format_ok and not files_changed and not unchanged_edit:
            test: TestRun = TestRun(passed=False, output=_format_feedback(generation.format_error))
            kind: str = "format"
        else:
            test = grade(workdir, test_command)
            kind = "" if test.passed else classify_test_failure(test.output, timed_out=test.timed_out)
            if unchanged_edit and not test.passed:
                previous: str = _previous_real_failure(history)
                if previous:
                    test = TestRun(passed=False, output=previous, timed_out=test.timed_out)
        record: AttemptRecord = AttemptRecord(
            index=len(history),
            engine=getattr(current, "name", "engine"),
            temperature=temperature,
            passed=test.passed,
            kind=kind,
            failing_tests=() if test.passed else failing_tests(test.output),
            changes=summarize_changes(before, after, editable_files),
            cause="" if test.passed else FAILURE_GUIDE.get(kind, FAILURE_GUIDE["other"])[0],
            excerpt="" if test.passed else failure_excerpt(test.output),
            locked_reverted=locked,
            fresh_start=fresh and bool(history),
            elapsed_seconds=round(now() - attempt_started, 3),
            unchanged_edit=unchanged_edit and not test.passed,
        )
        history.append(record)
        if on_attempt is not None:
            on_attempt(record)
        if is_escalation:
            if test.passed:
                escalation_solved = True
        else:
            local_attempts += 1
        if test.passed:
            stop_reason = "pass"

    first_pass: bool = bool(local_attempts >= 1 and history[0].passed)
    local_eventual: bool = any(item.passed for item in history[:local_attempts])
    eventual: bool = local_eventual or escalation_solved
    return RetryResult(
        first_pass=first_pass,
        local_eventual=local_eventual,
        eventual=eventual,
        attempts_used=len(history),
        local_attempts=local_attempts,
        escalated=escalated,
        escalation_solved=escalation_solved,
        attempts=tuple(history),
        elapsed_seconds=round(now() - started, 3),
        stop_reason=stop_reason,
        kinds=tuple(item.kind for item in history if item.kind),
    )


def _changed(before: dict[str, bytes], after: dict[str, bytes], files: tuple[str, ...]) -> bool:
    return any(before.get(path) != after.get(path) for path in files)


def _is_unchanged_edit(generation: EngineGeneration, *, files_changed: bool) -> bool:
    """An applied edit that left the editable bytes untouched is not a format miss."""
    if files_changed or generation.format_ok:
        return False
    if generation.format_error == "unchanged":
        return True
    return "Applied edit to " in (generation.raw_output or "")


def _format_feedback(format_error: str) -> str:
    cleaned: str = strip_aider_banner(format_error)
    if not cleaned or cleaned == "unchanged":
        cleaned = "no editable file changed"
    return f"format: {cleaned}"[:600]


def _previous_real_failure(history: list[AttemptRecord]) -> str:
    """Last test excerpt that is not an edit-format or banner report."""
    for item in reversed(history):
        text: str = strip_aider_banner(item.excerpt)
        if not text or item.kind == "format" or text.startswith("format:"):
            continue
        return text
    return ""


def _revert_paths(workdir: Path, baseline: dict[str, bytes], paths: tuple[str, ...]) -> None:
    for relative in paths:
        target: Path = workdir / relative
        if relative in baseline:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(baseline[relative])
        elif target.is_file():
            target.unlink()
