"""Scorecard columns for one-shot and Best-of-5 rates."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BestOfTaskResult:
    engine: str
    difficulty: str
    task_id: str
    passed_at_1: bool
    passed_best: bool
    generations: int
    elapsed_seconds: float
    format_errors: int
    failure_reason: str = ""


@dataclass(frozen=True, slots=True)
class BestOfScoreRow:
    engine: str
    difficulty: str
    total: int
    pass_at_1: int
    pass_at_5: int
    average_seconds: float
    format_error_rate: float

    @property
    def pass_at_1_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.pass_at_1 / self.total

    @property
    def pass_at_5_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.pass_at_5 / self.total


def aggregate_best_of(results: list[BestOfTaskResult]) -> list[BestOfScoreRow]:
    grouped: dict[tuple[str, str], list[BestOfTaskResult]] = defaultdict(list)
    for item in results:
        grouped[(item.engine, item.difficulty)].append(item)
    rows: list[BestOfScoreRow] = []
    for engine, difficulty in sorted(grouped):
        bucket: list[BestOfTaskResult] = grouped[(engine, difficulty)]
        generations: int = sum(item.generations for item in bucket)
        format_errors: int = sum(item.format_errors for item in bucket)
        rows.append(
            BestOfScoreRow(
                engine=engine,
                difficulty=difficulty,
                total=len(bucket),
                pass_at_1=sum(1 for item in bucket if item.passed_at_1),
                pass_at_5=sum(1 for item in bucket if item.passed_best),
                average_seconds=sum(item.elapsed_seconds for item in bucket) / len(bucket),
                format_error_rate=(format_errors / generations) if generations else 0.0,
            )
        )
    return rows


def render_best_of_scorecard(rows: list[BestOfScoreRow]) -> str:
    lines: list[str] = [
        "engine\tdifficulty\ttotal\tpass_at_1\tpass_at_5\t"
        "pass_at_1_rate\tpass_at_5_rate\tavg_seconds\tformat_error_rate"
    ]
    for row in rows:
        lines.append(
            f"{row.engine}\t{row.difficulty}\t{row.total}\t{row.pass_at_1}\t"
            f"{row.pass_at_5}\t{row.pass_at_1_rate:.0%}\t{row.pass_at_5_rate:.0%}\t"
            f"{row.average_seconds:.1f}\t{row.format_error_rate:.0%}"
        )
    return "\n".join(lines)


def top_failure_reasons(
    results: list[BestOfTaskResult],
    *,
    limit: int = 3,
) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for item in results:
        if item.passed_best or not item.failure_reason:
            continue
        counts[item.failure_reason] += 1
    return counts.most_common(limit)
