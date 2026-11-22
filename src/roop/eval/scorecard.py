"""Build a simple success-rate table from task statuses + rounds JSONL."""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from roop.orchestrator.tasks import TaskStore


@dataclass(frozen=True, slots=True)
class ScorecardRow:
    difficulty: str
    total: int
    done: int
    blocked: int
    pending: int

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.done / self.total


def engine_commit_hash(repo_root: Path | None = None) -> str:
    root: Path = repo_root or Path(__file__).resolve().parents[3]
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unknown"
    return (completed.stdout or "").strip() or "unknown"


def build_scorecard(database_path: Path) -> list[ScorecardRow]:
    store: TaskStore = TaskStore(database_path)
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    for task in store.list_tasks():
        difficulty: str = _difficulty_from_features(task.feature_ids)
        totals[difficulty] += 1
        buckets[difficulty][task.status.value] += 1
    rows: list[ScorecardRow] = []
    for difficulty in sorted(totals.keys()):
        counts = buckets[difficulty]
        rows.append(
            ScorecardRow(
                difficulty=difficulty,
                total=totals[difficulty],
                done=counts.get("done", 0),
                blocked=counts.get("blocked", 0),
                pending=counts.get("pending", 0) + counts.get("running", 0),
            )
        )
    return rows


def render_scorecard(
    rows: list[ScorecardRow],
    *,
    engine_commit: str | None = None,
) -> str:
    commit: str = engine_commit if engine_commit is not None else engine_commit_hash()
    lines: list[str] = [
        f"engine_commit\t{commit}",
        "difficulty\ttotal\tdone\tblocked\tpending\tsuccess",
    ]
    for row in rows:
        lines.append(
            f"{row.difficulty}\t{row.total}\t{row.done}\t{row.blocked}\t"
            f"{row.pending}\t{row.success_rate:.0%}"
        )
    return "\n".join(lines)


def summarize_rounds(rounds_path: Path) -> str:
    if not rounds_path.is_file():
        return "(no rounds.jsonl)"
    green: int = 0
    red: int = 0
    for line in rounds_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("green") is True:
            green += 1
        elif row.get("green") is False:
            red += 1
    return f"rounds green={green} red={red} file={rounds_path}"


def _difficulty_from_features(feature_ids: str) -> str:
    parts: list[str] = [item.strip() for item in feature_ids.split(",") if item.strip()]
    for item in parts:
        if item in {"easy", "medium", "hard"}:
            return item
    return "unknown"
