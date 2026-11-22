"""Night batch runner + morning report + launchd template (Phase 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from roop.context.roles import AgentRole
from roop.harness.fs_guard import WriteGuard
from roop.orchestrator.loop import OrchestratorLoop, TickResult
from roop.orchestrator.tasks import TaskStatus, TaskStore


@dataclass(frozen=True, slots=True)
class NightRunResult:
    """Summary of a night/batch queue drain."""

    ticks: int
    green: int
    red: int
    blocked: int
    pending: int
    report_path: Path | None = None
    tick_results: list[TickResult] = field(default_factory=list)

    @property
    def did_work(self) -> bool:
        return self.ticks > 0 and any(item.did_work for item in self.tick_results)


class NightScheduler:
    """Drain the task queue with real executor ticks and write a report."""

    def __init__(
        self,
        project_root: Path,
        database_path: Path,
        *,
        role: AgentRole = AgentRole.CODER,
        dry_run: bool = False,
        max_ticks: int = 50,
    ) -> None:
        self._project_root: Path = project_root.resolve()
        self._database_path: Path = database_path
        self._role: AgentRole = role
        self._dry_run: bool = dry_run
        self._max_ticks: int = max_ticks
        self._guard: WriteGuard = WriteGuard(self._project_root)

    def run(self) -> NightRunResult:
        loop: OrchestratorLoop = OrchestratorLoop.from_database(
            self._database_path,
            project_root=self._project_root,
            role=self._role,
            build_context=True,
            execute=True,
            dry_run=self._dry_run,
        )
        tick_results: list[TickResult] = loop.run_until_idle(max_ticks=self._max_ticks)
        store: TaskStore = TaskStore(self._database_path)
        green: int = sum(1 for item in tick_results if item.green is True)
        red: int = sum(1 for item in tick_results if item.green is False)
        blocked: int = len(store.list_tasks(status=TaskStatus.BLOCKED))
        pending: int = len(store.list_tasks(status=TaskStatus.PENDING))
        report: str = _render_report(
            project_root=self._project_root,
            ticks=tick_results,
            green=green,
            red=red,
            blocked=blocked,
            pending=pending,
            dry_run=self._dry_run,
        )
        stamp: str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path: Path = self._guard.write_text(
            Path(WriteGuard.AGENT_DIR_NAME) / "reports" / f"night-{stamp}.md",
            report,
        )
        self._guard.write_text(
            Path(WriteGuard.AGENT_DIR_NAME) / "reports" / "latest.md",
            report,
        )
        return NightRunResult(
            ticks=len([item for item in tick_results if item.did_work]),
            green=green,
            red=red,
            blocked=blocked,
            pending=pending,
            report_path=report_path,
            tick_results=tick_results,
        )


def write_launchd_plist(
    *,
    project_root: Path,
    hour: int = 2,
    minute: int = 0,
    dry_run: bool = True,
) -> Path:
    """Write a launchd plist template under ``.agent/scheduler/`` (not loaded)."""
    guard: WriteGuard = WriteGuard(project_root.resolve())
    roop_bin: str = "roop"
    venv_roop: Path = Path(__file__).resolve().parents[3] / ".venv" / "bin" / "roop"
    if venv_roop.is_file():
        roop_bin = str(venv_roop)
    dry_flag: str = "\n        <string>--dry-run</string>" if dry_run else ""
    label: str = "com.roop.night"
    plist: str = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{roop_bin}</string>
    <string>night</string>
    <string>--project</string>
    <string>{project_root.resolve()}</string>{dry_flag}
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{hour}</integer>
    <key>Minute</key>
    <integer>{minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{project_root.resolve()}/.agent/logs/night.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>{project_root.resolve()}/.agent/logs/night.stderr.log</string>
  <key>WorkingDirectory</key>
  <string>{project_root.resolve()}</string>
</dict>
</plist>
"""
    readme: str = (
        "# Roop scheduler\n\n"
        "Plist is written but **not** loaded automatically.\n\n"
        "```bash\n"
        f"cp .agent/scheduler/{label}.plist ~/Library/LaunchAgents/\n"
        f"launchctl load ~/Library/LaunchAgents/{label}.plist\n"
        "```\n"
    )
    guard.write_text(
        Path(WriteGuard.AGENT_DIR_NAME) / "scheduler" / "README.md",
        readme,
    )
    return guard.write_text(
        Path(WriteGuard.AGENT_DIR_NAME) / "scheduler" / f"{label}.plist",
        plist,
    )


def _render_report(
    *,
    project_root: Path,
    ticks: list[TickResult],
    green: int,
    red: int,
    blocked: int,
    pending: int,
    dry_run: bool,
) -> str:
    stamp: str = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines: list[str] = [
        "# Roop night report",
        "",
        f"- Generated: `{stamp}`",
        f"- Project: `{project_root}`",
        f"- Dry run: `{dry_run}`",
        f"- Green ticks: {green}",
        f"- Red ticks: {red}",
        f"- Blocked tasks: {blocked}",
        f"- Pending tasks: {pending}",
        "",
        "## Tick log",
        "",
    ]
    if not ticks:
        lines.append("- (no ticks)")
    for item in ticks:
        marker: str = ""
        if item.green is True:
            marker = " GREEN"
        elif item.green is False:
            marker = " RED"
        lines.append(
            f"- task={item.task_id} did_work={item.did_work}{marker}: {item.message}"
        )
    lines.append("")
    return "\n".join(lines)
