"""engine.py - WorkflowEngine Protocol + PGCheckpointerEngine.

T0033 — Durable Execution Adapter.

5-method Protocol:
  - start(workflow, *, input)         -> WorkflowRun
  - signal(run_id, signal)             -> None
  - query(run_id, query)               -> Any
  - cancel(run_id, reason)             -> None
  - get_status(run_id)                 -> WorkflowStatus

PGCheckpointerEngine is the in-process asyncio implementation that uses
SQLAlchemy async sessions over the 3-table schema from persistence.py.

Restart algorithm:
  1. SELECT * FROM workflow_checkpoints WHERE run_id = X
     ORDER BY created_at DESC LIMIT 1
  2. resume from the next step after that checkpoint.
  3. if no checkpoint, start from the first ready step.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .persistence import (
    WorkflowRunRow,
    init_schema,
    insert_run,
    latest_checkpoint,
    list_checkpoints,
    list_runs_by_status,
    make_engine,
    make_session_factory,
    record_activity,
    safe_json_loads,
    update_run,
    write_checkpoint,
)
from .step import (
    ActivityContext,
    WorkflowStep,
)
from .workflow import (
    Query,
    Signal,
    Workflow,
    WorkflowRun,
    WorkflowStatus,
    new_run_id,
)

log = logging.getLogger("aios_kernel.workflows.engine")


# ---------- Engine protocol -------------------------------------------------


@runtime_checkable
class WorkflowEngine(Protocol):
    """Protocol surface for a durable workflow engine. 5 methods."""

    async def start(
        self, workflow: Workflow, *, input: dict[str, Any] | None = None
    ) -> WorkflowRun: ...

    async def signal(self, run_id: str, signal: Signal) -> None: ...

    async def query(self, run_id: str, query: Query) -> Any: ...

    async def cancel(self, run_id: str, reason: str) -> None: ...

    async def get_status(self, run_id: str) -> WorkflowStatus: ...


# ---------- Engine implementation ------------------------------------------


class PGCheckpointerEngine:
    """SQLAlchemy-async engine, PG checkpointer, 3 tables.

    One engine = one writer process (Phase A constraint). For multi-worker
    support (Phase B), add ``SELECT ... FOR UPDATE SKIP LOCKED`` on the
    ``pending``/``running`` rows.
    """

    def __init__(
        self,
        database_url: str,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        # Allow injection of a pre-built engine (test fixtures).
        if engine is not None:
            self._engine = engine
            self._session_factory = session_factory or make_session_factory(engine)
        else:
            self._engine = make_engine(database_url)
            self._session_factory = session_factory or make_session_factory(self._engine)
        self._cancel_flags: dict[str, bool] = {}

    # -- lifecycle -----------------------------------------------------------

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def init(self) -> None:
        """Create tables (idempotent). Call once before first start()."""
        await init_schema(self._engine)

    async def close(self) -> None:
        await self._engine.dispose()

    # -- 5-method surface ----------------------------------------------------

    async def start(
        self,
        workflow: Workflow,
        *,
        input: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> WorkflowRun:
        """Start a new run, then synchronously drive it to completion.

        `run_id`: optional explicit run id (default = uuid4 hex). Useful for
        tests that want to predict the id.
        """
        rid = run_id or new_run_id()
        in_payload = input or {}
        async with self._session_factory() as session:
            await insert_run(
                session,
                run_id=rid,
                workflow_id=workflow.id,
                input_json=in_payload,
            )
            await session.commit()
        # drive
        return await self._drive(workflow, rid, resume_from=None)

    async def resume(self, workflow: Workflow, run_id: str) -> WorkflowRun:
        """Resume a run that was started but not finished. The engine looks up
        the latest checkpoint and continues from the next step.

        Used by the kill-restart flow: after the engine is killed mid-run,
        a fresh engine instance can pick the run up via this entry point.
        """
        return await self._drive(workflow, run_id, resume_from="auto")

    async def signal(self, run_id: str, signal: Signal) -> None:
        """Deliver a signal. Phase A: only "cancel" is honored natively;
        other types are stored in run metadata for future use.
        """
        if signal.type == "cancel":
            self._cancel_flags[run_id] = True
            return
        # any other signal -> store in run metadata (no engine action)
        async with self._session_factory() as session:
            row = await session.get(WorkflowRunRow, run_id)
            if row is None:
                raise KeyError(f"no run {run_id!r}")
            meta = dict(row.input_json or {})
            signals = list(meta.get("signals", []))
            signals.append(
                {
                    "type": signal.type,
                    "payload": signal.payload,
                    "ts": datetime.now(UTC).isoformat(),
                }
            )
            meta["signals"] = signals
            row.input_json = meta
            await session.commit()

    async def query(self, run_id: str, query: Query) -> Any:
        """Read-only query. Supported types: "status", "step:<id>", "history"."""
        async with self._session_factory() as session:
            row = await session.get(WorkflowRunRow, run_id)
            if row is None:
                raise KeyError(f"no run {run_id!r}")
            if query.type == "status":
                return WorkflowStatus(row.status)
            if query.type == "history":
                cps = await list_checkpoints(session, run_id)
                return [
                    {
                        "step_id": c.step_id,
                        "step_index": c.step_index,
                        "attempt": c.attempt,
                        "status": c.status,
                        "created_at": c.created_at.isoformat()
                        if c.created_at
                        else None,
                    }
                    for c in cps
                ]
            if query.type.startswith("step:"):
                target = query.type.split(":", 1)[1]
                cps = await list_checkpoints(session, run_id)
                for c in cps:
                    if c.step_id == target:
                        return {
                            "step_id": c.step_id,
                            "step_index": c.step_index,
                            "attempt": c.attempt,
                            "status": c.status,
                            "state": safe_json_loads(c.state_json),
                        }
                return None
        raise ValueError(f"unsupported query type: {query.type!r}")

    async def cancel(self, run_id: str, reason: str) -> None:
        """Cancel a run. Sets the cancel flag and marks status=cancelled.

        If the run is already terminal (completed/failed/cancelled), this
        is a no-op.
        """
        self._cancel_flags[run_id] = True
        async with self._session_factory() as session:
            row = await session.get(WorkflowRunRow, run_id)
            if row is None:
                raise KeyError(f"no run {run_id!r}")
            if row.status in ("completed", "failed", "cancelled"):
                return
            await update_run(
                session,
                run_id=run_id,
                status="cancelled",
                error=f"cancelled: {reason}",
                completed_at=datetime.now(UTC),
            )
            await session.commit()

    async def get_status(self, run_id: str) -> WorkflowStatus:
        async with self._session_factory() as session:
            row = await session.get(WorkflowRunRow, run_id)
            if row is None:
                raise KeyError(f"no run {run_id!r}")
            return WorkflowStatus(row.status)

    # -- recovery entry point ----------------------------------------------

    async def recover_running(self, workflow: Workflow) -> list[WorkflowRun]:
        """Find all runs in 'running' or 'pending' state and resume them.

        Returns the list of completed/failed/cancelled runs after the
        recovery sweep.
        """
        async with self._session_factory() as session:
            pending_rows = await list_runs_by_status(session, "pending")
            running_rows = await list_runs_by_status(session, "running")
            candidates = [r.run_id for r in pending_rows] + [r.run_id for r in running_rows]
        out: list[WorkflowRun] = []
        for rid in candidates:
            try:
                run = await self.resume(workflow, rid)
            except Exception:  # noqa: BLE001
                log.exception("recover failed for run %s", rid)
                continue
            out.append(run)
        return out

    # -- internal: drive the workflow ---------------------------------------

    async def _drive(
        self,
        workflow: Workflow,
        run_id: str,
        resume_from: str | None,
    ) -> WorkflowRun:
        """Execute steps in topological order, with checkpoint + retry.

        resume_from:
          - None: full run (start() path)
          - "auto": query latest checkpoint, continue from the next step
                    (resume() path)
        """
        order = workflow.topological_order()
        # Determine resume cursor
        if resume_from == "auto":
            async with self._session_factory() as session:
                cp = await latest_checkpoint(session, run_id)
            if cp is not None:
                # already-ran step states from history -> mark complete
                async with self._session_factory() as session:
                    cps = await list_checkpoints(session, run_id)
                done_ids = {c.step_id for c in cps}
            else:
                done_ids = set()
        else:
            done_ids = set()

        # mark run as running (if not already)
        async with self._session_factory() as session:
            row = await session.get(WorkflowRunRow, run_id)
            if row is None:
                raise KeyError(f"no run {run_id!r}")
            if row.status in ("pending",):
                await update_run(
                    session,
                    run_id=run_id,
                    status="running",
                    started_at=datetime.now(UTC),
                )
            elif row.status in ("completed", "failed", "cancelled"):
                # already terminal -> return snapshot
                return _row_to_run(row)
            await session.commit()

        # Execute steps. Maintain completed_outputs map.
        completed_outputs = {}
        for idx, step in enumerate(order):
            if step.id in done_ids:
                async with self._session_factory() as session:
                    cps = await list_checkpoints(session, run_id)
                for c in cps:
                    if c.step_id == step.id and c.status == "completed":
                        state = safe_json_loads(c.state_json)
                        completed_outputs[step.id] = state.get("output", {})
                continue
            if self._cancel_flags.get(run_id):
                async with self._session_factory() as session:
                    await update_run(
                        session,
                        run_id=run_id,
                        status="cancelled",
                        error="cancelled before step start",
                        completed_at=datetime.now(UTC),
                    )
                    await session.commit()
                async with self._session_factory() as session:
                    row = await session.get(WorkflowRunRow, run_id)
                    return _row_to_run(row)
            dep_outputs = {dep: completed_outputs.get(dep, {}) for dep in step.depends_on}
            status, output, last_error = await self._execute_step(
                workflow, run_id, step, idx, order, dep_outputs
            )
            if status == "completed":
                async with self._session_factory() as session:
                    await update_run(
                        session, run_id=run_id, current_step=step.id
                    )
                    await write_checkpoint(
                        session,
                        run_id=run_id,
                        step_id=step.id,
                        step_index=idx,
                        state_json={"output": output},
                        attempt=1,
                        status="completed",
                    )
                    await session.commit()
                completed_outputs[step.id] = output or {}
                continue
            # failure -> mark run as failed
            async with self._session_factory() as session:
                await update_run(
                    session,
                    run_id=run_id,
                    status="failed",
                    current_step=step.id,
                    error=f"step {step.id!r} failed after retries: {last_error}",
                    completed_at=datetime.now(UTC),
                )
                # write a failed-step checkpoint (still useful for forensics)
                await write_checkpoint(
                    session,
                    run_id=run_id,
                    step_id=step.id,
                    step_index=idx,
                    state_json={"output": output or {}, "error": last_error},
                    attempt=step.effective_retry_policy().max_attempts,
                    status="failed",
                )
                await session.commit()
            async with self._session_factory() as session:
                row = await session.get(WorkflowRunRow, run_id)
                return _row_to_run(row)

        # all steps completed -> mark run completed
        async with self._session_factory() as session:
            await update_run(
                session,
                run_id=run_id,
                status="completed",
                current_step=order[-1].id if order else None,
                completed_at=datetime.now(UTC),
            )
            await session.commit()
            row = await session.get(WorkflowRunRow, run_id)
            return _row_to_run(row)

    async def _execute_step(
        self,
        workflow: Workflow,
        run_id: str,
        step: WorkflowStep,
        step_index: int,
        order: list[WorkflowStep],
        dep_outputs = None,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        """Run a single step with retry + timeout. Return (status, output, error).

        status is "completed" or "failed" (after exhausting retries).
        """
        policy = step.effective_retry_policy()
        last_output: dict[str, Any] | None = None
        last_error: str | None = None
        dep_outputs = dep_outputs or {}
        for attempt in range(1, policy.max_attempts + 1):
            # sleep before retry (no sleep on attempt 1)
            if attempt > 1:
                delay = policy.delay_for(attempt)
                if delay > 0:
                    await asyncio.sleep(delay)

            ctx = ActivityContext(
                run_id=run_id,
                step_id=step.id,
                attempt=attempt,
                input={"workflow_input": {"workflow_id": workflow.id}, "deps": dep_outputs},
                output=last_output or {},
                metadata={
                    "workflow_id": workflow.id,
                    "step_index": step_index,
                    "prev_outputs": dep_outputs,
                },
            )
            # record started
            async with self._session_factory() as session:
                await record_activity(
                    session,
                    run_id=run_id,
                    activity_id=step.activity.name,
                    step_id=step.id,
                    attempt=attempt,
                    status="started",
                    started_at=datetime.now(UTC),
                )
                await session.commit()

            try:
                if step.timeout_s is not None:
                    result = await asyncio.wait_for(
                        step.activity.execute(ctx), timeout=step.timeout_s
                    )
                else:
                    result = await step.activity.execute(ctx)
            except TimeoutError:
                last_error = f"timeout after {step.timeout_s}s"
                async with self._session_factory() as session:
                    await record_activity(
                        session,
                        run_id=run_id,
                        activity_id=step.activity.name,
                        step_id=step.id,
                        attempt=attempt,
                        status="failed",
                        error=last_error,
                        finished_at=datetime.now(UTC),
                    )
                    await session.commit()
                if attempt < policy.max_attempts:
                    async with self._session_factory() as session:
                        await record_activity(
                            session,
                            run_id=run_id,
                            activity_id=step.activity.name,
                            step_id=step.id,
                            attempt=attempt + 1,
                            status="retried",
                        )
                        await session.commit()
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                async with self._session_factory() as session:
                    await record_activity(
                        session,
                        run_id=run_id,
                        activity_id=step.activity.name,
                        step_id=step.id,
                        attempt=attempt,
                        status="failed",
                        error=last_error,
                        finished_at=datetime.now(UTC),
                    )
                    await session.commit()
                if attempt < policy.max_attempts:
                    async with self._session_factory() as session:
                        await record_activity(
                            session,
                            run_id=run_id,
                            activity_id=step.activity.name,
                            step_id=step.id,
                            attempt=attempt + 1,
                            status="retried",
                        )
                        await session.commit()
                continue

            # handle result
            if result.success:
                last_output = result.output
                async with self._session_factory() as session:
                    await record_activity(
                        session,
                        run_id=run_id,
                        activity_id=step.activity.name,
                        step_id=step.id,
                        attempt=attempt,
                        status="completed",
                        finished_at=datetime.now(UTC),
                    )
                    await session.commit()
                return ("completed", result.output, None)
            last_error = result.error or "activity returned success=False"
            async with self._session_factory() as session:
                await record_activity(
                    session,
                    run_id=run_id,
                    activity_id=step.activity.name,
                    step_id=step.id,
                    attempt=attempt,
                    status="failed",
                    error=last_error,
                    finished_at=datetime.now(UTC),
                )
                await session.commit()
            if attempt < policy.max_attempts:
                async with self._session_factory() as session:
                    await record_activity(
                        session,
                        run_id=run_id,
                        activity_id=step.activity.name,
                        step_id=step.id,
                        attempt=attempt + 1,
                        status="retried",
                    )
                    await session.commit()
        return ("failed", last_output, last_error)


# ---------- helpers ---------------------------------------------------------


def _row_to_run(row: WorkflowRunRow) -> WorkflowRun:
    return WorkflowRun(
        run_id=row.run_id,
        workflow_id=row.workflow_id,
        status=WorkflowStatus(row.status),
        current_step=row.current_step,
        input=safe_json_loads(row.input_json),
        output=safe_json_loads(row.output_json),
        error=row.error,
        started_at=row.started_at.isoformat() if row.started_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
    )
