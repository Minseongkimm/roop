"""Roop CLI entrypoint: doctor, analyze, tick stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from roop import __version__
from roop.analyze.stub import AnalyzeResult, execute_analyze
from roop.doctor import DoctorCheck, execute_doctor
from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import TaskStore

app: typer.Typer = typer.Typer(
    name="roop",
    help="Roop — local autonomous coding agent engine",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    """Roop Phase 0 CLI."""


@app.command("version")
def version_command() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command("doctor")
def doctor_command(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        help="Optional project path to check for a git repo",
    ),
) -> None:
    """Check git, ripgrep, and local Ollama availability."""
    checks: list[DoctorCheck] = execute_doctor(target_path=path)
    failed: int = 0
    for check in checks:
        mark: str = "ok" if check.is_ok else "FAIL"
        typer.echo(f"[{mark}] {check.name}: {check.detail}")
        if not check.is_ok:
            failed += 1
    if failed:
        raise typer.Exit(code=1)


@app.command("analyze")
def analyze_command(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Scaffold minimal ``.agent/`` knowledge tree (Phase 0 stub)."""
    result: AnalyzeResult = execute_analyze(path)
    stacks: str = ", ".join(result.detected_stacks) if result.detected_stacks else "unknown"
    typer.echo(f"Analyzed: {result.target_root}")
    typer.echo(f"Stacks: {stacks}")
    typer.echo(f"Agent root: {result.agent_root}")
    for relative in result.created_files:
        typer.echo(f"  + .agent/{relative}")


@app.command("tick")
def tick_command(
    db: Path = typer.Option(
        Path(".agent/roop-tasks.sqlite3"),
        "--db",
        help="SQLite task database path",
    ),
) -> None:
    """Run one sequential orchestrator tick against the SQLite queue."""
    loop: OrchestratorLoop = OrchestratorLoop.from_database(db)
    result: TickResult = loop.tick()
    typer.echo(result.message)
    if not result.did_work:
        raise typer.Exit(code=0)


@app.command("enqueue")
def enqueue_command(
    title: str = typer.Argument(..., help="Task title"),
    db: Path = typer.Option(
        Path(".agent/roop-tasks.sqlite3"),
        "--db",
        help="SQLite task database path",
    ),
) -> None:
    """Enqueue a pending task (Phase 0 helper for tick demos)."""
    store: TaskStore = TaskStore(db)
    task = store.create_task(title)
    typer.echo(f"enqueued #{task.id}: {task.title}")


if __name__ == "__main__":
    app()
