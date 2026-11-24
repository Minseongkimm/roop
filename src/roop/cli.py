"""Roop CLI entrypoint: doctor, analyze, task manager, tick."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from roop import __version__
from roop.analyze.stub import AnalyzeResult, execute_analyze
from roop.context.builder import BuildResult, ContextBuilder
from roop.context.roles import AgentRole
from roop.doctor import DoctorCheck, execute_doctor
from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import (
    DEFAULT_PRIORITY,
    Task,
    TaskStatus,
    TaskStore,
    TaskTransitionError,
)

app: typer.Typer = typer.Typer(
    name="roop",
    help="Roop — local autonomous coding agent engine",
    no_args_is_help=True,
)
tasks_app: typer.Typer = typer.Typer(help="Inspect and manage the SQLite task queue")
eval_app: typer.Typer = typer.Typer(help="Evaluation suite enqueue / run")
app.add_typer(tasks_app, name="tasks")
app.add_typer(eval_app, name="eval")

DEFAULT_DB: Path = Path(".agent/roop-tasks.sqlite3")
DEFAULT_EVAL_DB: Path = Path(".agent/roop-eval.sqlite3")


@app.callback()
def main_callback() -> None:
    """Roop Phase 6 CLI."""


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
    """Scan project read-only and fill ``.agent/`` (Phase 1 analyzer)."""
    result: AnalyzeResult = execute_analyze(path)
    stacks: str = ", ".join(result.detected_stacks) if result.detected_stacks else "unknown"
    typer.echo(f"Analyzed: {result.target_root}")
    typer.echo(f"Stacks: {stacks}")
    typer.echo(f"Agent root: {result.agent_root}")
    if result.facts.package_name:
        typer.echo(
            f"Package: {result.facts.package_name}@{result.facts.package_version or '?'}"
        )
    for relative in result.created_files:
        typer.echo(f"  + .agent/{relative}")


@app.command("tick")
def tick_command(
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
    project: Optional[Path] = typer.Option(
        None,
        "--project",
        help="Project root for context packet build (defaults to db parent/.agent → parent)",
    ),
    role: str = typer.Option(
        "coder",
        "--role",
        help="Role: planner|coder|reviewer|tester",
    ),
    no_context: bool = typer.Option(
        False,
        "--no-context",
        help="Skip context packet build in placeholder mode",
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Call model + harness + verifier (Phase 4–5)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Execute with synthetic JSON (no Ollama)",
    ),
) -> None:
    """Run one orchestrator tick. Use --execute/--dry-run for real harness."""
    agent_role: AgentRole = _parse_role(role)
    project_root: Path | None = _resolve_project_root(db=db, project=project)
    should_execute: bool = execute or dry_run
    if should_execute and project_root is None:
        typer.echo("--execute/--dry-run requires a resolvable --project", err=True)
        raise typer.Exit(code=1)
    loop: OrchestratorLoop = OrchestratorLoop.from_database(
        db,
        project_root=None if no_context and not should_execute else project_root,
        role=agent_role,
        build_context=not no_context,
        execute=should_execute,
        dry_run=dry_run,
    )
    result: TickResult = loop.tick()
    typer.echo(result.message)
    if not result.did_work:
        raise typer.Exit(code=0)


@app.command("night")
def night_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Project root",
    ),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
    role: str = typer.Option("coder", "--role", help="Default role for ticks"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Drain queue with synthetic model output",
    ),
    max_ticks: int = typer.Option(50, "--max-ticks", help="Safety cap on ticks"),
    max_seconds: Optional[float] = typer.Option(
        None,
        "--max-seconds",
        help="Optional wall-clock hard stop; commits wip/ branch when hit",
    ),
) -> None:
    """Drain the queue and write a morning report under ``.agent/reports/``."""
    from roop.scheduler.night import NightRunResult, NightScheduler

    agent_role: AgentRole = _parse_role(role)
    database: Path = db if db.is_absolute() else project / db
    scheduler: NightScheduler = NightScheduler(
        project,
        database,
        role=agent_role,
        dry_run=dry_run,
        max_ticks=max_ticks,
        max_seconds=max_seconds,
    )
    result: NightRunResult = scheduler.run()
    typer.echo(
        f"night done ticks={result.ticks} green={result.green} "
        f"red={result.red} blocked={result.blocked} stop={result.stop_reason}"
    )
    if result.wip_branch:
        typer.echo(f"wip: {result.wip_branch}")
    if result.rounds_path:
        typer.echo(f"rounds: {result.rounds_path}")
    typer.echo(f"report: {result.report_path}")


@app.command("schedule-plist")
def schedule_plist_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Project root",
    ),
    hour: int = typer.Option(2, "--hour", help="Local hour for launchd"),
    minute: int = typer.Option(0, "--minute", help="Local minute for launchd"),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--live",
        help="Generate plist that passes --dry-run to night (default dry-run)",
    ),
) -> None:
    """Write a launchd plist template under ``.agent/scheduler/`` (not loaded)."""
    from roop.scheduler.night import write_launchd_plist

    path: Path = write_launchd_plist(
        project_root=project,
        hour=hour,
        minute=minute,
        dry_run=dry_run,
    )
    typer.echo(f"wrote {path}")
    typer.echo("Install manually via launchctl when ready (see .agent/scheduler/README.md)")


@app.command("context")
def context_command(
    task_id: int = typer.Argument(..., help="Task id"),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
    project: Optional[Path] = typer.Option(
        None,
        "--project",
        help="Project root containing .agent/",
    ),
    role: str = typer.Option(
        "coder",
        "--role",
        help="Role for context packet: planner|coder|reviewer|tester",
    ),
    feedback: str = typer.Option(
        "",
        "--feedback",
        help="Optional verifier feedback to include",
    ),
    budget: int = typer.Option(8000, "--budget", help="Token budget for the packet"),
    no_slices: bool = typer.Option(
        False,
        "--no-slices",
        help="Skip ripgrep code slices",
    ),
) -> None:
    """Build a role-scoped context packet under ``.agent/packets/``."""
    agent_role: AgentRole = _parse_role(role)
    project_root: Path | None = _resolve_project_root(db=db, project=project)
    if project_root is None:
        typer.echo("project root required (--project)", err=True)
        raise typer.Exit(code=1)
    store: TaskStore = TaskStore(db)
    try:
        task: Task = store.get_task(task_id)
    except KeyError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(code=1) from err
    builder: ContextBuilder = ContextBuilder(project_root, token_budget=budget)
    result: BuildResult = builder.build_and_write(
        task,
        agent_role,
        verifier_feedback=feedback,
        include_code_slices=not no_slices,
    )
    packet = result.packet
    typer.echo(
        f"packet task={packet.task_id} role={packet.role.value} "
        f"tokens={packet.estimated_tokens}/{packet.token_budget}"
        + (" truncated" if packet.truncated else "")
    )
    if result.markdown_path:
        typer.echo(f"  md: {result.markdown_path}")
    if result.json_path:
        typer.echo(f"  json: {result.json_path}")


@app.command("enqueue")
def enqueue_command(
    title: str = typer.Argument(..., help="Task title"),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
    description: str = typer.Option("", "--description", help="Task description"),
    feature: Optional[list[str]] = typer.Option(
        None,
        "--feature",
        help="Related feature id (repeatable)",
    ),
    priority: int = typer.Option(DEFAULT_PRIORITY, "--priority", help="Lower runs first"),
    depends_on: Optional[list[int]] = typer.Option(
        None,
        "--depends-on",
        help="Prerequisite task id (repeatable)",
    ),
    allow_paths: str = typer.Option(
        ".agent/**",
        "--allow-paths",
        help="Write allow paths for later executor phases",
    ),
    acceptance_criteria: str = typer.Option(
        "",
        "--ac",
        help="Acceptance criteria string",
    ),
    verify: str = typer.Option(
        "",
        "--verify",
        help="Verification command (executed in Phase 5)",
    ),
) -> None:
    """Enqueue a pending task into the SQLite queue."""
    from roop.eval.suite import is_noop_verify_command

    if is_noop_verify_command(verify):
        typer.echo(
            "refusing enqueue: provide a real --verify command (not empty/true/:)",
            err=True,
        )
        raise typer.Exit(code=1)
    store: TaskStore = TaskStore(db)
    feature_ids: str = ",".join(feature) if feature else ""
    task: Task = store.create_task(
        title,
        description=description,
        feature_ids=feature_ids,
        priority=priority,
        depends_on=depends_on or (),
        allow_paths=allow_paths,
        acceptance_criteria=acceptance_criteria,
        verify_command=verify,
    )
    deps: str = ",".join(str(item) for item in task.depends_on) or "-"
    typer.echo(
        f"enqueued #{task.id}: {task.title} "
        f"[priority={task.priority} depends_on={deps}]"
    )


@app.command("block")
def block_command(
    task_id: int = typer.Argument(..., help="Task id"),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
    reason: str = typer.Option("blocked via CLI", "--reason", help="Block reason"),
) -> None:
    """Mark a running or pending task blocked via running→blocked or force path."""
    store: TaskStore = TaskStore(db)
    task: Task = store.get_task(task_id)
    try:
        if task.status == TaskStatus.PENDING:
            store.transition(task_id, TaskStatus.RUNNING)
            updated: Task = store.transition(
                task_id, TaskStatus.BLOCKED, reason=reason
            )
        elif task.status == TaskStatus.RUNNING:
            updated = store.transition(task_id, TaskStatus.BLOCKED, reason=reason)
        else:
            typer.echo(
                f"cannot block task #{task_id} from status {task.status.value}",
                err=True,
            )
            raise typer.Exit(code=1)
    except TaskTransitionError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(code=1) from err
    typer.echo(f"blocked #{updated.id}: {updated.block_reason or reason}")


@app.command("unblock")
def unblock_command(
    task_id: int = typer.Argument(..., help="Task id"),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
) -> None:
    """Move a blocked task back to pending."""
    store: TaskStore = TaskStore(db)
    try:
        updated: Task = store.transition(task_id, TaskStatus.PENDING)
    except TaskTransitionError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(code=1) from err
    typer.echo(f"unblocked #{updated.id}: {updated.title}")


@eval_app.command("list")
def eval_list_command(
    suite: Optional[Path] = typer.Option(
        None,
        "--suite",
        help="Eval manifest path (default: evals/v1/manifest.json)",
    ),
) -> None:
    """List tasks in an eval suite."""
    from roop.eval.suite import default_suite_path, load_suite

    manifest: Path = suite or default_suite_path()
    loaded = load_suite(manifest)
    typer.echo(f"suite: {loaded.name} ({len(loaded.tasks)} tasks)")
    for item in loaded.tasks:
        typer.echo(f"- {item.id}\t{item.difficulty}\t{item.title}")


@eval_app.command("enqueue")
def eval_enqueue_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Target project root",
    ),
    suite: Optional[Path] = typer.Option(
        None,
        "--suite",
        help="Eval manifest path",
    ),
    db: Path = typer.Option(DEFAULT_EVAL_DB, "--db", help="Eval SQLite path"),
    task: Optional[list[str]] = typer.Option(
        None,
        "--task",
        help="Optional task id filter (repeatable)",
    ),
) -> None:
    """Enqueue eval suite tasks into a dedicated database."""
    from roop.eval.runner import enqueue_suite
    from roop.eval.suite import default_suite_path, load_suite

    manifest: Path = suite or default_suite_path()
    database: Path = db if db.is_absolute() else project / db
    loaded = load_suite(manifest)
    result = enqueue_suite(
        project_root=project,
        suite=loaded,
        database_path=database,
        task_ids=list(task) if task else None,
    )
    typer.echo(
        f"enqueued suite={result.suite_name} tasks={len(result.task_ids)} "
        f"db={result.database_path}"
    )
    for task_id in result.task_ids:
        typer.echo(f"  #{task_id}")


@eval_app.command("scorecard")
def eval_scorecard_command(
    db: Path = typer.Option(DEFAULT_EVAL_DB, "--db", help="Eval SQLite path"),
    project: Optional[Path] = typer.Option(
        None,
        "--project",
        help="Optional project root for rounds.jsonl summary",
    ),
) -> None:
    """Print done/blocked success rates for an eval database."""
    from roop.eval.scorecard import build_scorecard, render_scorecard, summarize_rounds

    database: Path = db
    if project is not None and not db.is_absolute():
        database = project / db
    from roop.eval.scorecard import engine_commit_hash

    rows = build_scorecard(database)
    typer.echo(render_scorecard(rows, engine_commit=engine_commit_hash()))
    if project is not None:
        rounds = project / ".agent" / "runs" / "rounds.jsonl"
        typer.echo(summarize_rounds(rounds))


@eval_app.command("run")
def eval_run_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Target project root",
    ),
    suite: Optional[Path] = typer.Option(
        None,
        "--suite",
        help="Eval manifest path",
    ),
    db: Path = typer.Option(DEFAULT_EVAL_DB, "--db", help="Eval SQLite path"),
    task: Optional[list[str]] = typer.Option(
        None,
        "--task",
        help="Optional task id filter (repeatable)",
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Run executor ticks after enqueue",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Use synthetic model output",
    ),
    max_ticks: int = typer.Option(100, "--max-ticks", help="Tick safety cap"),
) -> None:
    """Enqueue an eval suite and optionally execute ticks."""
    from roop.eval.runner import run_suite
    from roop.eval.suite import default_suite_path

    manifest: Path = suite or default_suite_path()
    database: Path = db if db.is_absolute() else project / db
    result = run_suite(
        project_root=project,
        suite_path=manifest,
        database_path=database,
        task_ids=list(task) if task else None,
        execute=execute,
        dry_run=dry_run,
        max_ticks=max_ticks,
    )
    typer.echo(
        f"eval suite={result.suite_name} enqueued={len(result.enqueued.task_ids)} "
        f"ticks={len([item for item in result.tick_results if item.did_work])}"
    )
    if result.tamper is not None and not result.tamper.ok:
        typer.echo(f"TAMPER: {result.tamper.detail}", err=True)
        raise typer.Exit(code=2)


@eval_app.command("compare")
def eval_compare_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=False,
        file_okay=False,
        dir_okay=True,
        help="Workspace for per-task scratch directories and the scorecard",
    ),
    engine: str = typer.Option(..., "--engine", help="roop or aider"),
    split: str = typer.Option("heldout", "--split", help="practice or heldout"),
    difficulty: Optional[str] = typer.Option(
        None,
        "--difficulty",
        help="Optional easy or medium filter",
    ),
    suite: Optional[Path] = typer.Option(None, "--suite", help="Eval manifest path"),
) -> None:
    """Run Best-of-5 for one engine. The harness grades every sample."""
    from roop.eval.best_score import render_best_of_scorecard, aggregate_best_of
    from roop.eval.compare import build_engine, load_compare_suite, run_compare

    try:
        selected = build_engine(engine)
    except ValueError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(code=1) from err
    results = run_compare(
        engine=selected,
        suite=load_compare_suite(suite),
        workspace=project,
        split=split,
        difficulty=difficulty,
    )
    typer.echo(render_best_of_scorecard(aggregate_best_of(results)))
    typer.echo(f"tasks={len(results)} workspace={project}")


@eval_app.command("retry")
def eval_retry_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=False,
        file_okay=False,
        dir_okay=True,
        help="Workspace for per-task scratch directories, results.jsonl and summary.txt",
    ),
    split: str = typer.Option("heldout", "--split", help="practice or heldout"),
    difficulty: Optional[str] = typer.Option(
        None,
        "--difficulty",
        help="Optional filter: v1 easy or medium, v2 single or multi",
    ),
    task: Optional[list[str]] = typer.Option(None, "--task", help="Only these task ids (repeatable)"),
    max_local: int = typer.Option(3, "--max-local", help="Local attempts per task"),
    escalate: bool = typer.Option(False, "--escalate/--no-escalate", help="Hand failed tasks to an API model"),
    escalate_preset: Optional[str] = typer.Option(None, "--escalate-preset", help="e.g. groq"),
    escalate_base_url: Optional[str] = typer.Option(None, "--escalate-base-url"),
    escalate_model: Optional[str] = typer.Option(None, "--escalate-model"),
    escalate_key_env: Optional[str] = typer.Option(None, "--escalate-key-env", help="Env var NAME holding the key"),
    suite: Optional[Path] = typer.Option(
        None,
        "--suite",
        help="Eval manifest path (default evals/v1/manifest.json; v2 is evals/v2/manifest.json)",
    ),
    attempt_timeout: Optional[float] = typer.Option(
        None,
        "--attempt-timeout",
        help="Seconds before the Aider process group is killed (default 240, 600 for several files)",
    ),
) -> None:
    """Failure-aware retry loop (Aider + local model), optional API escalation."""
    from roop.engines.aider_engine import AiderEngine
    from roop.engines.escalation import build_escalation_engine, escalation_config
    from roop.eval.compare import load_compare_suite
    from roop.eval.retry_eval import run_retry_eval

    escalation_engine = None
    if escalate or escalate_preset:
        config = escalation_config(
            enabled=True,
            preset=escalate_preset,
            base_url=escalate_base_url,
            model=escalate_model,
            key_env=escalate_key_env,
        )
        problem: str = config.problem()
        if problem:
            typer.echo(f"escalation unavailable: {problem}", err=True)
            raise typer.Exit(code=1)
        escalation_engine = build_escalation_engine(config)
        typer.echo(f"escalation: {config.label} via {config.base_url} (key from ${config.key_env})")

    def on_attempt(task_id: str, record) -> None:  # type: ignore[no-untyped-def]
        state: str = "pass" if record.passed else record.kind
        typer.echo(f"  {task_id} attempt {record.index + 1} [{record.engine}] {state} ({record.elapsed_seconds:.0f}s)")

    rows = run_retry_eval(
        engine=AiderEngine(timeout_seconds=attempt_timeout) if attempt_timeout else AiderEngine(),
        suite=load_compare_suite(suite),
        workspace=project,
        split=split,
        difficulty=difficulty,
        task_ids=list(task) if task else None,
        max_local_attempts=max_local,
        escalation_engine=escalation_engine,
        on_attempt=on_attempt,
    )
    typer.echo((project / "summary.txt").read_text(encoding="utf-8").rstrip())
    typer.echo(f"tasks={len(rows)} workspace={project}")


@eval_app.command("overnight")
def eval_overnight_command(
    project: Path = typer.Option(
        ...,
        "--project",
        exists=False,
        file_okay=False,
        dir_okay=True,
        help="Workspace for per-task worktrees, results.jsonl and summary.txt",
    ),
    split: str = typer.Option("heldout", "--split", help="practice or heldout"),
    difficulty: Optional[str] = typer.Option(None, "--difficulty"),
    task: Optional[list[str]] = typer.Option(None, "--task", help="Only these task ids (repeatable)"),
    suite: Optional[Path] = typer.Option(None, "--suite"),
    base_model: str = typer.Option(
        "ollama_chat/qwen2.5-coder:7b",
        "--base-model",
        help="Local Ollama model, or an openai/ model when --base-url is set",
    ),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="OpenAI-compatible base URL for the base model"),
    base_key_env: str = typer.Option("OPENROUTER_API_KEY", "--base-key-env"),
    fallback_model: str = typer.Option("qwen/qwen3-coder", "--fallback-model"),
    fallback_base_url: str = typer.Option("https://openrouter.ai/api/v1", "--fallback-base-url"),
    fallback_key_env: str = typer.Option("OPENROUTER_API_KEY", "--fallback-key-env"),
    max_attempts: int = typer.Option(3, "--max-attempts"),
    attempt_timeout: float = typer.Option(600.0, "--attempt-timeout"),
    max_cost_usd: float = typer.Option(5.0, "--max-cost-usd"),
) -> None:
    """Local base model, one OpenRouter fallback, hard attempt and dollar caps."""
    from roop.engines.routing import ModelSpec, RouteConfig, build_routed_engine, local_attempts
    from roop.eval.compare import load_compare_suite
    from roop.eval.retry_eval import run_retry_eval

    config = RouteConfig(
        base=ModelSpec(name=base_model, base_url=base_url or "", key_env=base_key_env if base_url else ""),
        fallback=ModelSpec(name=fallback_model, base_url=fallback_base_url, key_env=fallback_key_env),
        max_attempts=max_attempts,
        attempt_timeout_seconds=attempt_timeout,
        max_cost_usd=max_cost_usd,
    )
    problem: str = config.problem()
    if problem:
        typer.echo(f"overnight unavailable: {problem}", err=True)
        raise typer.Exit(code=1)
    base_engine = build_routed_engine(config.base, timeout_seconds=attempt_timeout)
    fallback = config.fallback
    assert fallback is not None
    fallback_engine = build_routed_engine(fallback, timeout_seconds=attempt_timeout)
    base_n, fallback_n = local_attempts(config)
    typer.echo(
        f"route: base {base_engine.name} | fallback {fallback.name} "
        f"via {fallback.base_url} (key from ${fallback.key_env})"
    )
    typer.echo(
        f"caps: attempts={config.max_attempts} timeout={attempt_timeout:.0f}s max_usd={max_cost_usd}"
    )

    def on_attempt(task_id: str, record) -> None:  # type: ignore[no-untyped-def]
        state: str = "pass" if record.passed else record.kind
        typer.echo(
            f"  {task_id} attempt {record.index + 1} [{record.model or record.engine}] {state} "
            f"({record.elapsed_seconds:.0f}s) tokens={record.input_tokens}/{record.output_tokens} "
            f"cache={record.cached_tokens} usd={record.cost_usd:.6f}"
        )

    rows = run_retry_eval(
        engine=base_engine,
        suite=load_compare_suite(suite),
        workspace=project,
        split=split,
        difficulty=difficulty,
        task_ids=list(task) if task else None,
        max_local_attempts=base_n,
        escalation_engine=fallback_engine if fallback_n else None,
        escalation_attempts=fallback_n,
        max_seconds=config.max_attempts * attempt_timeout,
        max_cost_usd=max_cost_usd,
        on_attempt=on_attempt,
    )
    typer.echo((project / "summary.txt").read_text(encoding="utf-8").rstrip())
    typer.echo(f"tasks={len(rows)} workspace={project}")


@tasks_app.command("list")
def tasks_list_command(
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status: pending|running|done|blocked|cancelled",
    ),
) -> None:
    """List tasks in the queue."""
    store: TaskStore = TaskStore(db)
    filter_status: TaskStatus | None = None
    if status is not None:
        try:
            filter_status = TaskStatus(status)
        except ValueError as err:
            typer.echo(f"invalid status: {status}", err=True)
            raise typer.Exit(code=1) from err
    tasks: list[Task] = store.list_tasks(status=filter_status)
    if not tasks:
        typer.echo("(no tasks)")
        return
    for task in tasks:
        deps: str = ",".join(str(item) for item in task.depends_on) or "-"
        features: str = task.feature_ids or "-"
        typer.echo(
            f"#{task.id}\t{task.status.value}\tp={task.priority}\t"
            f"retry={task.retry_count}/{task.max_retries}\t"
            f"deps={deps}\tfeat={features}\t{task.title}"
        )


@tasks_app.command("show")
def tasks_show_command(
    task_id: int = typer.Argument(..., help="Task id"),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="SQLite task database path"),
) -> None:
    """Show one task in detail."""
    store: TaskStore = TaskStore(db)
    try:
        task: Task = store.get_task(task_id)
    except KeyError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(code=1) from err
    lines: list[str] = [
        f"id: {task.id}",
        f"title: {task.title}",
        f"status: {task.status.value}",
        f"priority: {task.priority}",
        f"description: {task.description or '-'}",
        f"feature_ids: {task.feature_ids or '-'}",
        f"allow_paths: {task.allow_paths}",
        f"depends_on: {','.join(str(item) for item in task.depends_on) or '-'}",
        f"acceptance_criteria: {task.acceptance_criteria or '-'}",
        f"verify_command: {task.verify_command or '-'}",
        f"retry_count: {task.retry_count}/{task.max_retries}",
        f"block_reason: {task.block_reason or '-'}",
        f"updated_at: {task.updated_at or '-'}",
    ]
    typer.echo("\n".join(lines))


def _parse_role(value: str) -> AgentRole:
    try:
        return AgentRole(value.lower())
    except ValueError as err:
        typer.echo(
            "invalid role: use planner|coder|reviewer|tester",
            err=True,
        )
        raise typer.Exit(code=1) from err


def _resolve_project_root(
    *,
    db: Path,
    project: Path | None,
) -> Path | None:
    if project is not None:
        return project.resolve()
    resolved_db: Path = db.expanduser().resolve()
    # Typical layout: <project>/.agent/roop-tasks.sqlite3
    if resolved_db.parent.name == ".agent":
        return resolved_db.parent.parent
    if (resolved_db.parent / ".agent").is_dir():
        return resolved_db.parent
    cwd_agent: Path = Path.cwd() / ".agent"
    if cwd_agent.is_dir():
        return Path.cwd()
    return None


if __name__ == "__main__":
    app()
