"""Sequential orchestrator tick (Phase 4–6: execute + verify + retry)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from roop.adapters.model import ModelAdapter
from roop.context.roles import AgentRole
from roop.orchestrator.tasks import Task, TaskStatus, TaskStore


@dataclass(frozen=True, slots=True)
class TickResult:
    """Outcome of a single orchestrator tick."""

    did_work: bool
    task_id: int | None
    message: str
    packet_path: str | None = None
    green: bool | None = None
    round_log_path: str | None = None


class OrchestratorLoop:
    """Claim runnable task, optionally execute role, verify, retry or done."""

    def __init__(
        self,
        store: TaskStore,
        *,
        project_root: Path | None = None,
        role: AgentRole = AgentRole.CODER,
        build_context: bool = True,
        execute: bool = False,
        dry_run: bool = False,
        model: ModelAdapter | None = None,
    ) -> None:
        self._store: TaskStore = store
        self._project_root: Path | None = (
            project_root.resolve() if project_root is not None else None
        )
        self._role: AgentRole = role
        self._build_context: bool = build_context
        self._execute: bool = execute
        self._dry_run: bool = dry_run
        self._model: ModelAdapter | None = model

    @classmethod
    def from_database(
        cls,
        database_path: Path,
        *,
        project_root: Path | None = None,
        role: AgentRole = AgentRole.CODER,
        build_context: bool = True,
        execute: bool = False,
        dry_run: bool = False,
        model: ModelAdapter | None = None,
    ) -> OrchestratorLoop:
        return cls(
            TaskStore(database_path),
            project_root=project_root,
            role=role,
            build_context=build_context,
            execute=execute,
            dry_run=dry_run,
            model=model,
        )

    def tick(self) -> TickResult:
        task: Task | None = self._store.next_runnable()
        if task is None:
            if self._store.has_pending_waiting_on_deps():
                return TickResult(
                    did_work=False,
                    task_id=None,
                    message="queue idle: pending tasks waiting on dependencies",
                )
            return TickResult(did_work=False, task_id=None, message="queue empty")
        self._store.transition(task.id, TaskStatus.RUNNING)
        if self._execute and self._project_root is not None:
            return self._tick_execute(task)
        packet_path: str | None = None
        if self._build_context and self._project_root is not None:
            from roop.context.builder import BuildResult, ContextBuilder

            builder: ContextBuilder = ContextBuilder(self._project_root)
            result: BuildResult = builder.build_and_write(task, self._role)
            packet_path = str(result.markdown_path) if result.markdown_path else None
        self._store.transition(task.id, TaskStatus.DONE)
        message: str = f"tick completed placeholder for task {task.id}: {task.title}"
        if packet_path:
            message = f"{message} (packet: {packet_path})"
        return TickResult(
            did_work=True,
            task_id=task.id,
            message=message,
            packet_path=packet_path,
            green=True,
        )

    def _tick_execute(self, task: Task) -> TickResult:
        from roop.executor.agent import AgentExecutor, ExecutionResult
        from roop.memory.lessons import Lesson, LessonStore
        from roop.telemetry.rounds import (
            RoundLog,
            RoundRecord,
            estimate_tokens,
            extract_error_signature,
            extract_test_counts,
            patch_diff_stat,
            utc_now_iso,
        )
        from roop.verifier.engine import Verifier, VerifyResult

        assert self._project_root is not None
        previous_saw: str = task.last_failure_feedback
        feedback: str = (
            f"PREVIOUS_SAW:\n{previous_saw}" if previous_saw else ""
        )
        executor: AgentExecutor = AgentExecutor(
            self._project_root,
            self._store,
            model=self._model,
            dry_run=self._dry_run,
        )
        try:
            execution: ExecutionResult = executor.execute(
                task,
                self._role,
                verifier_feedback=feedback,
            )
        except Exception as exc:
            failure = f"EXECUTION ERROR: {type(exc).__name__}: {exc}"
            self._store.set_failure_feedback(task.id, failure)
            self._store.transition(task.id, TaskStatus.PENDING, reason=failure[:200])
            log_path = self._append_round(
                RoundRecord(
                    ts=utc_now_iso(),
                    task_id=task.id,
                    role=self._role.value,
                    green=False,
                    exit_code=None,
                    error_signature=extract_error_signature(failure),
                    tests_ran=None,
                    tests_passed=None,
                    tokens_est=None,
                    model="",
                    message=failure,
                    status="error",
                )
            )
            return TickResult(
                did_work=True,
                task_id=task.id,
                message=f"tick ERROR task {task.id} → pending: {type(exc).__name__}",
                round_log_path=str(log_path) if log_path else None,
            )
        verifier: Verifier = Verifier(self._project_root)
        try:
            verify: VerifyResult = verifier.verify(task, execution)
        except Exception:
            if execution.transaction is not None:
                execution.transaction.rollback()
            raise

        packet_path: str | None = execution.packet_path
        command_out: str = ""
        if execution.command is not None:
            command_out = (
                f"{execution.command.stdout}\n{execution.command.stderr}"
            )
        if verify.saw:
            command_out = f"{command_out}\n{verify.saw}"
        for detail in verify.details:
            command_out = f"{command_out}\n{detail}"
        tests_ran, tests_passed = extract_test_counts(command_out)
        diff_stat = patch_diff_stat(execution.patches)
        tokens_est = estimate_tokens(execution.model_raw)

        if verify.green:
            if execution.transaction is not None:
                execution.transaction.commit()
            self._store.set_failure_feedback(task.id, "")
            self._store.transition(task.id, TaskStatus.DONE)
            LessonStore(self._project_root).append(
                Lesson(
                    task_id=task.id,
                    summary=f"{self._role.value} GREEN — {task.title}",
                    evidence=verify.saw[:200],
                )
            )
            message = (
                f"tick GREEN task {task.id}: {task.title} "
                f"({execution.message})"
            )
            log_path = self._append_round(
                RoundRecord(
                    ts=utc_now_iso(),
                    task_id=task.id,
                    role=self._role.value,
                    green=True,
                    exit_code=verify.exit_code,
                    error_signature="",
                    tests_ran=tests_ran,
                    tests_passed=tests_passed,
                    tokens_est=tokens_est,
                    model=execution.model,
                    diff_stat=diff_stat,
                    patches_applied=diff_stat.get("applied", 0),
                    patches_total=diff_stat.get("files", 0),
                    message=message,
                    status="done",
                )
            )
            return TickResult(
                did_work=True,
                task_id=task.id,
                message=message,
                packet_path=packet_path,
                green=True,
                round_log_path=str(log_path) if log_path else None,
            )
        if execution.transaction is not None:
            execution.transaction.rollback()

        saw: str = verify.feedback()
        self._store.set_failure_feedback(task.id, saw)

        # Allow at least a couple of repair attempts before treating an identical
        # failure signature as a hard block (max_retries still applies).
        if previous_saw and previous_saw == saw and task.retry_count >= 2:
            self._store.transition(
                task.id,
                TaskStatus.BLOCKED,
                reason="identical SAW repeated",
            )
            message = f"tick BLOCKED task {task.id}: identical SAW repeated"
            log_path = self._append_round(
                RoundRecord(
                    ts=utc_now_iso(),
                    task_id=task.id,
                    role=self._role.value,
                    green=False,
                    exit_code=verify.exit_code,
                    error_signature=extract_error_signature(saw),
                    tests_ran=tests_ran,
                    tests_passed=tests_passed,
                    tokens_est=tokens_est,
                    model=execution.model,
                    diff_stat=diff_stat,
                    patches_applied=diff_stat.get("applied", 0),
                    patches_total=diff_stat.get("files", 0),
                    message=message,
                    status="blocked",
                )
            )
            return TickResult(
                did_work=True,
                task_id=task.id,
                message=message,
                packet_path=packet_path,
                green=False,
                round_log_path=str(log_path) if log_path else None,
            )

        retried: Task = self._store.transition(
            task.id,
            TaskStatus.PENDING,
            reason=saw[:200],
        )
        if retried.status == TaskStatus.BLOCKED:
            message = (
                f"tick BLOCKED task {task.id}: max retries — "
                f"{retried.block_reason}"
            )
            status = "blocked"
        else:
            message = (
                f"tick RED task {task.id} → pending "
                f"(retry {retried.retry_count}/{retried.max_retries})"
            )
            status = "pending"
        log_path = self._append_round(
            RoundRecord(
                ts=utc_now_iso(),
                task_id=task.id,
                role=self._role.value,
                green=False,
                exit_code=verify.exit_code,
                error_signature=extract_error_signature(saw),
                tests_ran=tests_ran,
                tests_passed=tests_passed,
                tokens_est=tokens_est,
                model=execution.model,
                diff_stat=diff_stat,
                patches_applied=diff_stat.get("applied", 0),
                patches_total=diff_stat.get("files", 0),
                message=message,
                status=status,
            )
        )
        return TickResult(
            did_work=True,
            task_id=task.id,
            message=message,
            packet_path=packet_path,
            green=False,
            round_log_path=str(log_path) if log_path else None,
        )

    def _append_round(self, record: object) -> Path | None:
        if self._project_root is None:
            return None
        from roop.telemetry.rounds import RoundLog, RoundRecord

        if not isinstance(record, RoundRecord):
            return None
        return RoundLog(self._project_root).append(record)

    def run_until_idle(self, *, max_ticks: int = 100) -> list[TickResult]:
        results: list[TickResult] = []
        for _ in range(max_ticks):
            result: TickResult = self.tick()
            results.append(result)
            if not result.did_work:
                break
        return results
