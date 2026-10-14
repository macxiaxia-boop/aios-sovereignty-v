"""P7: database-backed workflow leases and fenced checkpoint ownership.

Only isolated SQLite databases; production PostgreSQL and crash-kill
need separate verification. External side effects are not invoked.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from aios_kernel.workflows import (
    ActivityResult,
    PGCheckpointerEngine,
    StepMeta,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    from_callable,
)
from aios_kernel.workflows.engine import WorkflowLeaseBusy
from aios_kernel.workflows.persistence import (
    WorkflowLeaseRow,
    acquire_workflow_lease,
    release_workflow_lease,
    renew_workflow_lease,
)


@pytest.fixture
async def engine(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'leases.db').as_posix()}"
    engine = PGCheckpointerEngine(url)
    await engine.init()
    try:
        yield engine
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_only_one_live_lease_and_fence_strictly_increases(engine):
    async with engine._session_factory() as session:
        t1 = await acquire_workflow_lease(
            session, run_id="shared", owner_id="worker-a", ttl_s=100,
        )
        await session.commit()
    assert t1 == 1
    async with engine._session_factory() as session:
        t2 = await acquire_workflow_lease(
            session, run_id="shared", owner_id="worker-b", ttl_s=100,
        )
        await session.commit()
    assert t2 is None

    async with engine._session_factory() as session:
        assert await release_workflow_lease(
            session, run_id="shared", owner_id="worker-a", fencing_token=t1,
        )
        await session.commit()

    async with engine._session_factory() as session:
        t3 = await acquire_workflow_lease(
            session, run_id="shared", owner_id="worker-b", ttl_s=100,
        )
        await session.commit()
    assert t3 == 2

    async with engine._session_factory() as session:
        assert not await release_workflow_lease(
            session, run_id="shared", owner_id="worker-a", fencing_token=t1,
        )
        assert not await renew_workflow_lease(
            session, run_id="shared", owner_id="worker-a",
            fencing_token=t1, ttl_s=100,
        )
        assert await renew_workflow_lease(
            session, run_id="shared", owner_id="worker-b",
            fencing_token=t3, ttl_s=100,
        )
        await session.commit()


@pytest.mark.asyncio
async def test_lease_takeover_after_expiry_rejects_old_owner(engine):
    async with engine._session_factory() as session:
        token_a = await acquire_workflow_lease(
            session, run_id="expired", owner_id="a",
        )
        await session.commit()
    async with engine._session_factory() as session:
        await session.execute(
            update(WorkflowLeaseRow)
            .where(WorkflowLeaseRow.run_id == "expired")
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=10))
        )
        await session.commit()
    async with engine._session_factory() as session:
        token_b = await acquire_workflow_lease(
            session, run_id="expired", owner_id="b",
        )
        await session.commit()
    assert token_b == token_a + 1
    async with engine._session_factory() as session:
        assert not await renew_workflow_lease(
            session, run_id="expired", owner_id="a",
            fencing_token=token_a,
        )
        await session.commit()


@pytest.mark.asyncio
async def test_concurrent_resume_cannot_execute_while_lease_owned(engine):
    started = asyncio.Event()
    proceed = asyncio.Event()
    calls = []

    async def slow(ctx):
        calls.append(ctx.run_id)
        started.set()
        await proceed.wait()
        return ActivityResult(success=True, output={"data": 1})

    wf = Workflow(
        id="lease-race", name="lease-race",
        steps=[WorkflowStep(
            meta=StepMeta(id="slow", name="slow"),
            activity=from_callable("slow", slow),
        )],
    )

    first = asyncio.create_task(engine.start(wf, run_id="lease-race-run"))
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        with pytest.raises(WorkflowLeaseBusy):
            await engine.resume(wf, "lease-race-run")
        assert calls == ["lease-race-run"]
    finally:
        proceed.set()

    first_result = await asyncio.wait_for(first, timeout=10)
    assert first_result.status == WorkflowStatus.COMPLETED
    assert first_result.output["steps"]["slow"] == {"data": 1}


@pytest.mark.asyncio
async def test_new_run_reuses_released_lease_without_reexecuting(engine):
    calls = []

    async def act(ctx):
        calls.append(ctx.run_id)
        return ActivityResult(success=True, output={"ok": True})

    wf = Workflow(
        id="completed-no-replay", name="completed-no-replay",
        steps=[WorkflowStep(
            meta=StepMeta(id="step", name="step"),
            activity=from_callable("step", act),
        )],
    )
    done = await engine.start(wf, run_id="one")
    snap = await engine.resume(wf, "one")
    assert done.status == snap.status == WorkflowStatus.COMPLETED
    assert calls == ["one"]
