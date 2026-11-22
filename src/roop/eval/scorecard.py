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
    local_pass: int = 0
    api_pass: int = 0
    fail: int = 0
    api_skipped: int = 0
    api_calls: int = 0
    estimated_cost_usd: float = 0.0

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
    outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    api_calls: Counter[str] = Counter()
    costs: dict[str, float] = defaultdict(float)
    for task in store.list_tasks():
        difficulty: str = _difficulty_from_features(task.feature_ids)
        totals[difficulty] += 1
        buckets[difficulty][task.status.value] += 1
        outcomes[difficulty][_score_outcome(task.status.value, task.outcome)] += 1
        api_calls[difficulty] += int(task.api_calls)
        costs[difficulty] += float(task.estimated_cost_usd)
    rows: list[ScorecardRow] = []
    for difficulty in sorted(totals.keys()):
        counts = buckets[difficulty]
        outcome_counts = outcomes[difficulty]
        rows.append(
            ScorecardRow(
                difficulty=difficulty,
                total=totals[difficulty],
                done=counts.get("done", 0),
                blocked=counts.get("blocked", 0),
                pending=counts.get("pending", 0) + counts.get("running", 0),
                local_pass=outcome_counts.get("local_pass", 0),
                api_pass=outcome_counts.get("api_pass", 0),
                fail=outcome_counts.get("fail", 0),
                api_skipped=outcome_counts.get("api_skipped", 0),
                api_calls=api_calls[difficulty],
                estimated_cost_usd=costs[difficulty],
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
        "difficulty\ttotal\tdone\tblocked\tpending\tsuccess\t"
        "local_pass\tapi_pass\tfail\tapi_skipped\tapi_calls\testimated_cost_usd",
    ]
    rendered: list[ScorecardRow] = list(rows)
    if rows:
        rendered.append(_sum_rows(rows))
    for row in rendered:
        lines.append(
            f"{row.difficulty}\t{row.total}\t{row.done}\t{row.blocked}\t"
            f"{row.pending}\t{row.success_rate:.0%}\t{row.local_pass}\t"
            f"{row.api_pass}\t{row.fail}\t{row.api_skipped}\t{row.api_calls}\t"
            f"{row.estimated_cost_usd:.6f}"
        )
    return "\n".join(lines)


def summarize_rounds(rounds_path: Path) -> str:
    if not rounds_path.is_file():
        return "(no rounds.jsonl)"
    green: int = 0
    red: int = 0
    outcomes: Counter[str] = Counter()
    api_calls: int = 0
    cost: float = 0.0
    for line in rounds_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("green") is True:
            green += 1
        elif row.get("green") is False:
            red += 1
        outcome: str = str(row.get("outcome") or "")
        if outcome:
            outcomes[outcome] += 1
        api_calls += int(row.get("api_calls") or 0)
        cost += float(row.get("estimated_cost_usd") or 0.0)
    return (
        f"rounds green={green} red={red} file={rounds_path}\n"
        f"outcomes local_pass={outcomes.get('local_pass', 0)} "
        f"api_pass={outcomes.get('api_pass', 0)} "
        f"fail={outcomes.get('fail', 0)} "
        f"api_skipped={outcomes.get('api_skipped', 0)} "
        f"api_calls={api_calls} estimated_cost_usd={cost:.6f}"
    )


def _score_outcome(status: str, outcome: str) -> str:
    if outcome in {"local_pass", "api_pass", "fail", "api_skipped"}:
        return outcome
    if status == "done":
        return "local_pass"
    if status == "blocked":
        return "fail"
    return ""


def _sum_rows(rows: list[ScorecardRow]) -> ScorecardRow:
    return ScorecardRow(
        difficulty="all",
        total=sum(item.total for item in rows),
        done=sum(item.done for item in rows),
        blocked=sum(item.blocked for item in rows),
        pending=sum(item.pending for item in rows),
        local_pass=sum(item.local_pass for item in rows),
        api_pass=sum(item.api_pass for item in rows),
        fail=sum(item.fail for item in rows),
        api_skipped=sum(item.api_skipped for item in rows),
        api_calls=sum(item.api_calls for item in rows),
        estimated_cost_usd=sum(item.estimated_cost_usd for item in rows),
    )


def _difficulty_from_features(feature_ids: str) -> str:
    parts: list[str] = [item.strip() for item in feature_ids.split(",") if item.strip()]
    for item in parts:
        if item in {"easy", "medium", "hard"}:
            return item
    return "unknown"
