"""Sequential orchestrator tick (Phase 4–6: execute + verify + retry)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from roop.adapters.api import api_client_from_env, should_hand_off_to_api
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
        api_model: ModelAdapter | None = None,
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
        self._api_model: ModelAdapter | None = api_model

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
        api_model: ModelAdapter | None = None,
    ) -> OrchestratorLoop:
        return cls(
            TaskStore(database_path),
            project_root=project_root,
            role=role,
            build_context=build_context,
            execute=execute,
            dry_run=dry_run,
            model=model,
            api_model=api_model,
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
            estimate_tokens,
            extract_error_signature,
            extract_test_counts,
            patch_diff_stat,
            utc_now_iso,
        )
        from roop.verifier.engine import Verifier, VerifyResult

        assert self._project_root is not None
        started: float = time.monotonic()
        backend, api_adapter = self._resolve_backend(task)
        if backend == "api_skipped":
            self._store.set_outcome(task.id, "api_skipped")
            self._store.transition(
                task.id,
                TaskStatus.BLOCKED,
                reason="api_skipped",
            )
            message = f"tick API_SKIPPED task {task.id}: no API key"
            log_path = self._log_round(
                task=task,
                backend=backend,
                outcome="api_skipped",
                green=False,
                exit_code=None,
                error_signature="api_skipped",
                tests_ran=None,
                tests_passed=None,
                tokens_est=None,
                model="",
                diff_stat={},
                message=message,
                status="api_skipped",
                api_calls=0,
                estimated_cost_usd=0.0,
                started=started,
                timestamp=utc_now_iso(),
            )
            return TickResult(
                did_work=True,
                task_id=task.id,
                message=message,
                green=False,
                round_log_path=str(log_path) if log_path else None,
            )
        previous_saw: str = task.last_failure_feedback
        feedback: str = (
            f"PREVIOUS_SAW:\n{previous_saw}" if previous_saw else ""
        )
        executor: AgentExecutor = AgentExecutor(
            self._project_root,
            self._store,
            model=api_adapter if backend == "api" else self._model,
            dry_run=self._dry_run,
        )
        before_calls, before_cost = _adapter_usage(api_adapter)
        try:
            execution: ExecutionResult = executor.execute(
                task,
                self._role,
                verifier_feedback=feedback,
            )
        except Exception as exc:
            calls, cost = _usage_delta(api_adapter, before_calls, before_cost)
            self._store.add_usage(
                task.id,
                api_calls=calls,
                estimated_cost_usd=cost,
            )
            failure = f"EXECUTION ERROR: {type(exc).__name__}: {exc}"
            self._store.set_failure_feedback(task.id, failure)
            retried: Task = self._store.transition(
                task.id,
                TaskStatus.PENDING,
                reason=failure[:200],
            )
            if retried.status == TaskStatus.BLOCKED:
                self._mark_terminal_failure(task.id)
            log_path = self._log_round(
                task=task,
                backend=backend,
                outcome="fail",
                green=False,
                exit_code=None,
                error_signature=extract_error_signature(failure),
                tests_ran=None,
                tests_passed=None,
                tokens_est=None,
                model="",
                diff_stat={},
                message=failure,
                status="blocked" if retried.status == TaskStatus.BLOCKED else "error",
                api_calls=calls,
                estimated_cost_usd=cost,
                started=started,
                timestamp=utc_now_iso(),
            )
            return TickResult(
                did_work=True,
                task_id=task.id,
                message=f"tick ERROR task {task.id} → {retried.status.value}: {type(exc).__name__}",
                round_log_path=str(log_path) if log_path else None,
            )
        calls, cost = _usage_delta(api_adapter, before_calls, before_cost)
        self._store.add_usage(task.id, api_calls=calls, estimated_cost_usd=cost)
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
            outcome = "api_pass" if backend == "api" else "local_pass"
            self._store.set_failure_feedback(task.id, "")
            self._store.set_outcome(task.id, outcome)
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
            log_path = self._log_round(
                task=task,
                backend=backend,
                outcome=outcome,
                green=True,
                exit_code=verify.exit_code,
                error_signature="",
                tests_ran=tests_ran,
                tests_passed=tests_passed,
                tokens_est=tokens_est,
                model=execution.model,
                diff_stat=diff_stat,
                message=message,
                status="done",
                api_calls=calls,
                estimated_cost_usd=cost,
                started=started,
                timestamp=utc_now_iso(),
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
        if backend == "local":
            self._store.add_local_verify_failure(task.id)

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
            self._mark_terminal_failure(task.id)
            message = f"tick BLOCKED task {task.id}: identical SAW repeated"
            log_path = self._log_round(
                task=task,
                backend=backend,
                outcome="fail",
                green=False,
                exit_code=verify.exit_code,
                error_signature=extract_error_signature(saw),
                tests_ran=tests_ran,
                tests_passed=tests_passed,
                tokens_est=tokens_est,
                model=execution.model,
                diff_stat=diff_stat,
                message=message,
                status="blocked",
                api_calls=calls,
                estimated_cost_usd=cost,
                started=started,
                timestamp=utc_now_iso(),
            )
            return TickResult(
                did_work=True,
                task_id=task.id,
                message=message,
                packet_path=packet_path,
                green=False,
                round_log_path=str(log_path) if log_path else None,
            )

        retried = self._store.transition(
            task.id,
            TaskStatus.PENDING,
            reason=saw[:200],
        )
        if retried.status == TaskStatus.BLOCKED:
            self._mark_terminal_failure(task.id)
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
        log_path = self._log_round(
            task=task,
            backend=backend,
            outcome="fail",
            green=False,
            exit_code=verify.exit_code,
            error_signature=extract_error_signature(saw),
            tests_ran=tests_ran,
            tests_passed=tests_passed,
            tokens_est=tokens_est,
            model=execution.model,
            diff_stat=diff_stat,
            message=message,
            status=status,
            api_calls=calls,
            estimated_cost_usd=cost,
            started=started,
            timestamp=utc_now_iso(),
        )
        return TickResult(
            did_work=True,
            task_id=task.id,
            message=message,
            packet_path=packet_path,
            green=False,
            round_log_path=str(log_path) if log_path else None,
        )

    def _resolve_backend(self, task: Task) -> tuple[str, ModelAdapter | None]:
        if not should_hand_off_to_api(
            local_verify_failures=task.local_verify_failures,
            dry_run=self._dry_run,
        ):
            return "local", None
        if self._api_model is not None:
            return "api", self._api_model
        client = api_client_from_env()
        if client is None:
            return "api_skipped", None
        return "api", client

    def _mark_terminal_failure(self, task_id: int) -> None:
        current: Task = self._store.get_task(task_id)
        if current.outcome == "api_skipped":
            return
        if current.status == TaskStatus.BLOCKED:
            self._store.set_outcome(task_id, "fail")

    def _log_round(
        self,
        *,
        task: Task,
        backend: str,
        outcome: str,
        green: bool | None,
        exit_code: int | None,
        error_signature: str,
        tests_ran: int | None,
        tests_passed: int | None,
        tokens_est: int | None,
        model: str,
        diff_stat: dict[str, int],
        message: str,
        status: str,
        api_calls: int,
        estimated_cost_usd: float,
        started: float,
        timestamp: str,
    ) -> Path | None:
        from roop.telemetry.rounds import RoundRecord

        provider = "api" if backend == "api" else "local"
        if backend == "api_skipped":
            provider = "none"
        return self._append_round(
            RoundRecord(
                ts=timestamp,
                task_id=task.id,
                role=self._role.value,
                green=green,
                exit_code=exit_code,
                error_signature=error_signature,
                tests_ran=tests_ran,
                tests_passed=tests_passed,
                tokens_est=tokens_est,
                model=model,
                diff_stat=diff_stat,
                patches_applied=diff_stat.get("applied", 0),
                patches_total=diff_stat.get("files", 0),
                message=message,
                status=status,
                provider=provider,
                outcome=outcome,
                api_calls=api_calls,
                estimated_cost_usd=estimated_cost_usd,
                elapsed_seconds=round(time.monotonic() - started, 3),
            )
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


def _adapter_usage(model: ModelAdapter | None) -> tuple[int, float]:
    if model is None:
        return 0, 0.0
    calls: int = int(getattr(model, "calls", 0))
    cost: float = float(getattr(model, "estimated_cost_usd", 0.0))
    return calls, cost


def _usage_delta(
    model: ModelAdapter | None,
    before_calls: int,
    before_cost: float,
) -> tuple[int, float]:
    calls, cost = _adapter_usage(model)
    return max(0, calls - before_calls), max(0.0, cost - before_cost)
