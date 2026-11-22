"""Append-only JSONL round logs under ``.agent/runs/``."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from roop.harness.fs_guard import WriteGuard

_RAN_RE: re.Pattern[str] = re.compile(r"Ran\s+(\d+)\s+tests?", re.IGNORECASE)
_FAIL_RE: re.Pattern[str] = re.compile(
    r"FAILED\s*\(.*?failures=(\d+).*?\)|failures=(\d+)",
    re.IGNORECASE,
)
_ERROR_RE: re.Pattern[str] = re.compile(r"errors=(\d+)", re.IGNORECASE)
_OK_RE: re.Pattern[str] = re.compile(r"^\s*OK\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class RoundRecord:
    """One orchestrator execute tick, serialized to JSONL."""

    ts: str
    task_id: int
    role: str
    green: bool | None
    exit_code: int | None
    error_signature: str
    tests_ran: int | None
    tests_passed: int | None
    tokens_est: int | None
    model: str
    diff_stat: dict[str, int] = field(default_factory=dict)
    patches_applied: int = 0
    patches_total: int = 0
    message: str = ""
    status: str = ""

    def to_json(self) -> str:
        payload: dict[str, Any] = asdict(self)
        return json.dumps(payload, ensure_ascii=False)


class RoundLog:
    """Write round records to ``.agent/runs/rounds.jsonl``."""

    def __init__(self, project_root: Path) -> None:
        self._project_root: Path = project_root.resolve()
        self._guard: WriteGuard = WriteGuard(self._project_root)
        self._path: Path = (
            self._project_root / WriteGuard.AGENT_DIR_NAME / "runs" / "rounds.jsonl"
        )

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: RoundRecord) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json() + "\n")
        return self._path

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            text: str = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
        return rows


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def extract_error_signature(feedback: str, *, max_chars: int = 180) -> str:
    cleaned: str = " ".join(feedback.split())
    if not cleaned:
        return ""
    return cleaned[:max_chars]


def extract_test_counts(output: str) -> tuple[int | None, int | None]:
    """Return (tests_ran, tests_passed) from unittest-style output."""
    ran_match = _RAN_RE.search(output)
    if ran_match is None:
        return None, None
    ran: int = int(ran_match.group(1))
    if ran == 0:
        return 0, 0
    if _OK_RE.search(output):
        return ran, ran
    failures: int = 0
    fail_match = _FAIL_RE.search(output)
    if fail_match is not None:
        failures = int(fail_match.group(1) or fail_match.group(2) or "0")
    errors: int = 0
    error_match = _ERROR_RE.search(output)
    if error_match is not None:
        errors = int(error_match.group(1))
    passed: int = max(0, ran - failures - errors)
    return ran, passed


def patch_diff_stat(patches: list[Any]) -> dict[str, int]:
    applied: int = 0
    total: int = 0
    for item in patches:
        total += 1
        if getattr(item, "applied", False):
            applied += 1
    return {"files": total, "applied": applied}
