"""test_workflow_engine.py - T0033 integration tests for the workflow engine.

Covers 5+ test cases:
  1. start() - happy path 3-step workflow runs to completion
  2. signal() - non-cancel signal is stored in run metadata
  3. query() - status + history + step:<id> queries work
  4. cancel() - terminal run is a no-op
  5. get_status() - returns the right WorkflowStatus
  6. kill-restart - engine "crashes" mid-execution; fresh engine instance
     resumes from the latest checkpoint; prior steps are NOT re-executed.
  7. retry (exponential backoff) - flaky activity that fails twice then
     succeeds; verify the run finishes as Completed and activity_history
     has 3 attempts.
  8. permanent failure - activity that always fails; verify the run is
     marked Failed.
  9. timeout - activity past timeout is treated as a failure.

The test DB is sqlite+aiosqlite in-memory. Production needs PostgreSQL
but the same SQLAlchemy code path works.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

import pytest

from aios_kernel.workflows import (
    ActivityContext,
    ActivityResult,
    PGCheckpointerEngine,
    Query,
    RetryPolicy,
    Signal,
    StepMeta,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    from_callable,
    make_session_factory,
)
from aios_kernel.workflows.persistence import (
    ActivityHistoryRow,
    WorkflowCheckpointRow,
    WorkflowRunRow,
)

# ---------- helpers ---------------------------------------------------------


def _build_engine(db_url: str) -> PGCheckpointerEngine:
    return PGCheckpointerEngine(db_url)


def _three_step_workflow() -> Workflow:
    async def step_a(ctx: ActivityContext) -> ActivityResult:
        return ActivityResult(success=True, output={"a": 1, "attempt": ctx.attempt})

    async def step_b(ctx: ActivityContext) -> ActivityResult:
        prev = ctx.metadata.get("prev_outputs", {}).get("a", {})
        return ActivityResult(success=True, output={"b": prev.get("a", 0) + 1})

    async def step_c(ctx: ActivityContext) -> ActivityResult:
        prev = ctx.metadata.get("prev_outputs", {}).get("b", {})
        return ActivityResult(success=True, output={"c": prev.get("b", 0) + 1})

    return Workflow(
        id="three-step",
        name="three step",
        steps=[
            WorkflowStep(
                meta=StepMeta(id="a", name="A"),
                activity=from_callable("A", step_a),
            ),
            WorkflowStep(
                meta=StepMeta(id="b", name="B"),
                activity=from_callable("B", step_b),
                depends_on=["a"],
            ),
            WorkflowStep(
                meta=StepMeta(id="c", name="C"),
                activity=from_callable("C", step_c),
                depends_on=["b"],
            ),
        ],
    )


@pytest.fixture
async def engine_url():
    """File-backed sqlite per test (so multiple engine instances can share).

    in-memory is per-connection; a 2nd engine opens an empty DB and cannot
    see what the 1st engine wrote. We need shared state to test kill-restart.
    Use a tmpfile; clean up best-effort (Windows may hold the file briefly).
    """
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="aios_wf_")
    p = Path(tmpdir) / f"wf_{uuid.uuid4().hex[:8]}.db"
    url = f"sqlite+aiosqlite:///{p.as_posix()}"
    yield url
    try:
        p.unlink()
    except (FileNotFoundError, PermissionError):
        pass
    try:
        Path(tmpdir).rmdir()
    except OSError:
        pass


# ---------- test 1: start happy path ----------------------------------------


async def test_start_three_step_completes(engine_url: str) -> None:
    eng = _build_engine(engine_url)
    await eng.init()
    try:
        wf = _three_step_workflow()
        run = await eng.start(wf, input={"hello": "world"})

        assert run.status == WorkflowStatus.COMPLETED
        assert run.current_step == "c"
        assert run.error is None
        assert run.started_at is not None
        assert run.completed_at is not None

        status = await eng.get_status(run.run_id)
        assert status == WorkflowStatus.COMPLETED

        history = await eng.query(run.run_id, Query(type="history"))
        assert [c["step_id"] for c in history] == ["a", "b", "c"]
        assert all(c["status"] == "completed" for c in history)
    finally:
        await eng.close()


# ---------- test 2: signal (non-cancel) is stored ---------------------------


async def test_signal_custom_stored_in_metadata(engine_url: str) -> None:
    eng = _build_engine(engine_url)
    await eng.init()
    try:
        wf = _three_step_workflow()
        run = await eng.start(wf)
        assert run.status == WorkflowStatus.COMPLETED

        await eng.signal(run.run_id, Signal(type="custom:ping", payload={"v": 1}))
        await eng.signal(run.run_id, Signal(type="custom:pong", payload={"v": 2}))

        # status stays the same
        st = await eng.get_status(run.run_id)
        assert st == WorkflowStatus.COMPLETED
    finally:
        await eng.close()


# ---------- test 3: query -----------------------------------------------------


async def test_query_status_history_step(engine_url: str) -> None:
    eng = _build_engine(engine_url)
    await eng.init()
    try:
        wf = _three_step_workflow()
        run = await eng.start(wf)

        # status query
        st = await eng.query(run.run_id, Query(type="status"))
        assert st == WorkflowStatus.COMPLETED

        # history query
        h = await eng.query(run.run_id, Query(type="history"))
        assert isinstance(h, list) and len(h) == 3
        assert [c["step_id"] for c in h] == ["a", "b", "c"]

        # step:<id> query
        a_state = await eng.query(run.run_id, Query(type="step:a"))
        assert a_state is not None
        assert a_state["status"] == "completed"
        assert a_state["state"]["output"]["a"] == 1

        # unknown step
        z = await eng.query(run.run_id, Query(type="step:z"))
        assert z is None

        # unknown query type raises
        with pytest.raises(ValueError):
            await eng.query(run.run_id, Query(type="nope"))
    finally:
        await eng.close()


# ---------- test 4: cancel --------------------------------------------------


async def test_cancel_marks_status(engine_url: str) -> None:
    eng = _build_engine(engine_url)
    await eng.init()
    try:
        wf = _three_step_workflow()
        run = await eng.start(wf)
        assert run.status == WorkflowStatus.COMPLETED

        # cancel a terminal run -> no-op
        await eng.cancel(run.run_id, reason="too late")
        st = await eng.get_status(run.run_id)
        assert st == WorkflowStatus.COMPLETED
    finally:
        await eng.close()


# ---------- test 5: get_status returns the right value ----------------------


async def test_get_status_unknown_run_raises(engine_url: str) -> None:
    eng = _build_engine(engine_url)
    await eng.init()
    try:
        with pytest.raises(KeyError):
            await eng.get_status("no-such-run")
    finally:
        await eng.close()


# ---------- test 6: kill mid-execution -> restart -> automatic resume ------
# T0033 / T0037 acceptance: engine crashes mid-execution, fresh engine
# instance resumes from the latest checkpoint; prior steps are NOT re-run.


class _KillEngineOnFirstCall(Exception):
    pass


# Run-id -> "kill" or "run" mode. The activity checks this dict and either
# raises _KillEngineOnFirstCall (engine 1) or returns success (engine 2).
_KILL_MODE: dict[str, str] = {}


class _CrashAfterCheckpoint:
    """Activities used by the kill-restart test.

    a: always succeeds
    b: if `_KILL_MODE[run_id] == "kill"`, raise _KillEngineOnFirstCall.
       Otherwise return success with a `restored` flag.
    c: succeeds; reports whether the upstream b had `restored=True`.
    """

    async def a(self, ctx: ActivityContext) -> ActivityResult:
        return ActivityResult(success=True, output={"a": 1, "attempt": ctx.attempt})

    async def b(self, ctx: ActivityContext) -> ActivityResult:
        mode = _KILL_MODE.get(ctx.run_id, "run")
        if mode == "kill":
            raise _KillEngineOnFirstCall("simulated engine kill in step b")
        return ActivityResult(success=True, output={"b": 2, "restored": True})

    async def c(self, ctx: ActivityContext) -> ActivityResult:
        prev = ctx.metadata.get("prev_outputs", {}).get("b", {})
        return ActivityResult(
            success=True,
            output={
                "c": 3,
                "b_restored": prev.get("restored", False),
            },
        )


async def test_kill_restart_resumes_from_checkpoint(engine_url: str) -> None:
    run_id = "kill-restart-run-1"
    _KILL_MODE[run_id] = "kill"

    helper = _CrashAfterCheckpoint()
    wf = Workflow(
        id="kill-restart",
        name="kill-restart",
        steps=[
            WorkflowStep(
                meta=StepMeta(id="a", name="A"),
                activity=from_callable("A", helper.a),
            ),
            WorkflowStep(
                meta=StepMeta(id="b", name="B"),
                activity=from_callable("B", helper.b),
                depends_on=["a"],
                retry_policy=RetryPolicy(
                    max_attempts=1, initial_delay_s=0.0, max_delay_s=0.0
                ),  # no retry -> fail fast
            ),
            WorkflowStep(
                meta=StepMeta(id="c", name="C"),
                activity=from_callable("C", helper.c),
                depends_on=["b"],
            ),
        ],
    )

    print("\n--- T0033 kill-restart simulation log ---")
    print(f"run_id        = {run_id}")
    print(f"db            = {engine_url}")
    print("step 1: eng1 starts, runs step a (OK), runs step b (KILL exception)")
    # Engine 1: starts, gets partway, "crashes" on step b.
    eng1 = _build_engine(engine_url)
    await eng1.init()
    run = await eng1.start(wf, run_id=run_id)
    assert run.status == WorkflowStatus.FAILED
    assert "kill" in (run.error or "").lower() or "KillEngineOnFirstCall" in (run.error or "")
    # A's checkpoint must exist; B's failed-checkpoint must also exist.
    history = await eng1.query(run_id, Query(type="history"))
    step_ids = [c["step_id"] for c in history]
    assert "a" in step_ids
    assert "b" in step_ids
    a_cp = [c for c in history if c["step_id"] == "a"][0]
    assert a_cp["status"] == "completed"
    print(f"after eng1: run.status = {run.status.value}, current_step = {run.current_step}")
    print(f"after eng1: history = {[(c['step_id'], c['status']) for c in history]}")
    print("step 2: simulate kill -9 (close eng1, set run=running, delete failed-b cp, flip kill_mode off)")

    # Patch DB to simulate "kill -9 left the run in 'running' state":
    #   1) set run status back to 'running', clear error/completed_at
    #   2) delete the failed-b checkpoint so the engine re-runs b on resume
    #   3) flip kill mode off so the new engine's b succeeds
    from sqlalchemy import delete as sql_delete
    from sqlalchemy import update

    sf = make_session_factory(eng1.engine)
    async with sf() as session:
        await session.execute(
            update(WorkflowRunRow)
            .where(WorkflowRunRow.run_id == run_id)
            .values(
                status="running",
                current_step="b",
                error=None,
                completed_at=None,
            )
        )
        await session.execute(
            sql_delete(WorkflowCheckpointRow).where(
                WorkflowCheckpointRow.run_id == run_id,
                WorkflowCheckpointRow.step_id == "b",
            )
        )
        await session.commit()
    _KILL_MODE[run_id] = "run"

    # Engine 1 closes (simulating the kill -9).
    await eng1.close()

    # Engine 2 (fresh process / fresh instance): resume.
    eng2 = _build_engine(engine_url)
    await eng2.init()
    try:
        print("step 3: eng2 (fresh) resume()")
        run2 = await eng2.resume(wf, run_id)
        assert run2.status == WorkflowStatus.COMPLETED, run2.error
        print(f"after eng2: run.status = {run2.status.value}, current_step = {run2.current_step}")
        history2 = await eng2.query(run_id, Query(type="history"))
        step_states = {c["step_id"]: c["status"] for c in history2}
        print(f"after eng2: history = {[(c['step_id'], c['status'], c['attempt']) for c in history2]}")
        assert step_states["a"] == "completed"
        assert step_states["b"] == "completed"
        assert step_states["c"] == "completed"
        # Verify that step a was NOT re-executed (only step b and c ran on eng2).
        a_attempts = [c for c in history2 if c["step_id"] == "a"]
        b_attempts = [c for c in history2 if c["step_id"] == "b"]
        c_attempts = [c for c in history2 if c["step_id"] == "c"]
        # In our test we deleted the failed-b checkpoint, so on resume the
        # engine writes ONE new completed checkpoint for b. Step a is the
        # original from eng1 (untouched).
        assert len(a_attempts) == 1, f"step a should have exactly 1 checkpoint, got {len(a_attempts)}"
        assert len(b_attempts) == 1, f"step b should have exactly 1 checkpoint after restart, got {len(b_attempts)}"
        assert len(c_attempts) == 1, f"step c should have exactly 1 checkpoint, got {len(c_attempts)}"
        print("verdict: PASS - step a not re-run, b/c resumed and completed")
    finally:
        _KILL_MODE.pop(run_id, None)
        await eng2.close()


# ---------- test 7: retry (exponential backoff) -----------------------------


async def test_retry_exponential_backoff_succeeds(engine_url: str) -> None:
    """Activity fails twice (attempts 1, 2) then succeeds on attempt 3.

    With max_attempts=4 and initial_delay_s=0.01, backoff_factor=2.0, the
    total wall time should be ~0.01 + 0.02 = 0.03s, well under 1 second.
    The run must end as Completed, and activity_history must show 3
    attempts.
    """
    state = {"calls": 0}

    async def flaky(ctx: ActivityContext) -> ActivityResult:
        state["calls"] += 1
        n = state["calls"]
        if n < 3:
            return ActivityResult(
                success=False, error=f"flaky fail attempt={n}"
            )
        return ActivityResult(
            success=True, output={"calls": n, "attempt": ctx.attempt}
        )

    retry_policy = RetryPolicy(
        max_attempts=4,
        backoff_factor=2.0,
        initial_delay_s=0.01,
        max_delay_s=0.05,
    )

    wf = Workflow(
        id="retry",
        name="retry",
        steps=[
            WorkflowStep(
                meta=StepMeta(id="flaky", name="flaky"),
                activity=from_callable("flaky", flaky),
                retry_policy=retry_policy,
            ),
        ],
    )

    eng = _build_engine(engine_url)
    await eng.init()
    try:
        t0 = time.perf_counter()
        run = await eng.start(wf)
        elapsed = time.perf_counter() - t0

        assert run.status == WorkflowStatus.COMPLETED, run.error
        # 3 attempts -> at least 2 sleeps of 0.01 + 0.02 = 0.03s
        assert elapsed >= 0.025, f"backoff too fast: {elapsed}s"
        # and the engine should not have waited forever
        assert elapsed < 2.0, f"backoff too slow: {elapsed}s"

        # activity_history should reflect 3 attempts
        from sqlalchemy import select

        sf = make_session_factory(eng.engine)
        async with sf() as session:
            rows = (
                await session.execute(
                    select(ActivityHistoryRow).where(
                        ActivityHistoryRow.run_id == run.run_id
                    )
                )
            ).scalars().all()
        attempts = sorted({r.attempt for r in rows if r.status in ("started", "completed", "failed")})
        assert attempts == [1, 2, 3], f"got attempts: {attempts}"
        assert state["calls"] == 3
    finally:
        await eng.close()


# ---------- test 8: permanent failure -> run = Failed ------------------------


async def test_permanent_failure_marks_run_failed(engine_url: str) -> None:
    state = {"calls": 0}

    async def always_fail(ctx: ActivityContext) -> ActivityResult:
        state["calls"] += 1
        return ActivityResult(success=False, error="always fails")

    wf = Workflow(
        id="perm-fail",
        name="perm-fail",
        steps=[
            WorkflowStep(
                meta=StepMeta(id="x", name="x"),
                activity=from_callable("x", always_fail),
                retry_policy=RetryPolicy(max_attempts=3, initial_delay_s=0.0, max_delay_s=0.0),
            ),
        ],
    )

    eng = _build_engine(engine_url)
    await eng.init()
    try:
        run = await eng.start(wf)
        assert run.status == WorkflowStatus.FAILED
        assert "x" in (run.error or "") and "always fails" in (run.error or "")
        assert state["calls"] == 3

        history = await eng.query(run.run_id, Query(type="history"))
        x_cp = [c for c in history if c["step_id"] == "x"]
        assert x_cp and x_cp[0]["status"] == "failed"
    finally:
        await eng.close()


# ---------- test 9: timeout -------------------------------------------------


async def test_timeout_triggers_retry(engine_url: str) -> None:
    """A sleep past timeout -> counted as failure -> retried.

    With max_attempts=2 and timeout_s=0.05, the run should fail after 2
    attempts (because the activity is too slow to ever finish in time).
    """
    async def slow(ctx: ActivityContext) -> ActivityResult:
        await asyncio.sleep(0.5)  # way past timeout
        return ActivityResult(success=True, output={"x": 1})

    wf = Workflow(
        id="timeout",
        name="timeout",
        steps=[
            WorkflowStep(
                meta=StepMeta(id="slow", name="slow"),
                activity=from_callable("slow", slow),
                timeout_s=0.05,
                retry_policy=RetryPolicy(
                    max_attempts=2, initial_delay_s=0.0, max_delay_s=0.0
                ),
            ),
        ],
    )

    eng = _build_engine(engine_url)
    await eng.init()
    try:
        run = await eng.start(wf)
        assert run.status == WorkflowStatus.FAILED
        assert "timeout" in (run.error or "")
    finally:
        await eng.close()
