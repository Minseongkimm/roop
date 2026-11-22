from __future__ import annotations

import argparse
import sys
from pathlib import Path

from roop import __version__
from roop.analyze.stub import scaffold_agent_dir
from roop.doctor import CheckResult, run_doctor
from roop.orchestrator.loop import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="roop")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="Print version")
    doctor = sub.add_parser("doctor", help="Check local tooling")
    doctor.add_argument("--project", type=Path, default=None)
    analyze = sub.add_parser("analyze", help="Scaffold .agent/ only")
    analyze.add_argument("project", type=Path)
    enqueue = sub.add_parser("enqueue", help="Enqueue a goal for a project")
    enqueue.add_argument("project", type=Path)
    enqueue.add_argument("goal", type=str)
    tick = sub.add_parser("tick", help="Run one orchestrator tick")
    tick.add_argument("project", type=Path)
    return parser


def execute_doctor(project: Path | None) -> int:
    results: list[CheckResult] = run_doctor(project)
    exit_code: int = 0
    for result in results:
        mark: str = "OK" if result.ok else "FAIL"
        print(f"[{mark}] {result.name}: {result.detail}")
        if result.name != "ollama" and not result.ok:
            exit_code = 1
        if result.name == "ripgrep" and not result.ok:
            exit_code = 0 if exit_code == 0 else exit_code
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "doctor":
        return execute_doctor(args.project)
    if args.command == "analyze":
        written = scaffold_agent_dir(args.project)
        print(f"scaffolded {len(written)} files under {args.project / '.agent'}")
        return 0
    if args.command == "enqueue":
        orchestrator: Orchestrator = Orchestrator(args.project)
        task_id: int = orchestrator.enqueue(args.goal)
        print(f"enqueued task#{task_id}")
        return 0
    if args.command == "tick":
        orchestrator = Orchestrator(args.project)
        print(orchestrator.tick())
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
