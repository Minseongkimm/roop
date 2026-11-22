#!/usr/bin/env python3
"""Collect failed/blocked tasks into a short FAILURES.md."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from roop.orchestrator.tasks import TaskStatus, TaskStore  # noqa: E402


def _tail_lines(text: str, count: int = 20) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return "(no error text)"
    return "\n".join(lines[-count:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        action="append",
        required=True,
        help="SQLite task DB path (repeatable)",
    )
    parser.add_argument(
        "--out",
        default="FAILURES.md",
        help="Output markdown path",
    )
    args = parser.parse_args()
    sections: list[str] = ["# FAILURES", ""]
    found = 0
    for db_text in args.db:
        db_path = Path(db_text).expanduser().resolve()
        store = TaskStore(db_path)
        failed = [
            task
            for task in store.list_tasks()
            if task.status in {TaskStatus.BLOCKED, TaskStatus.PENDING}
            and task.last_failure_feedback.strip()
        ]
        if not failed:
            continue
        sections.append(f"## DB `{db_path}`")
        sections.append("")
        for task in failed:
            found += 1
            reason = task.block_reason or "failed"
            sections.append(f"### {task.title}")
            sections.append(f"- status: `{task.status.value}`")
            sections.append(f"- retries: `{task.retry_count}/{task.max_retries}`")
            sections.append(f"- cause: `{reason}`")
            sections.append("")
            sections.append("```")
            sections.append(_tail_lines(task.last_failure_feedback, 20))
            sections.append("```")
            sections.append("")
    if found == 0:
        sections.append("(no failed tasks with feedback)")
        sections.append("")
    out_path = Path(args.out).expanduser().resolve()
    out_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"wrote {out_path} ({found} failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
