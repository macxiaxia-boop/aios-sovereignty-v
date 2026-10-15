"""P7: effective worker identity and stable operation identity.

The idempotency key is intentionally stable across retries for provider
adapters, while the fencing token is unique per acquired execution lease.
This alone does not guarantee external platform exactly-once effects.
"""
from __future__ import annotations

import asyncio

import pytest

from aios_kernel.workflows import (
    ActivityResult,
    PGCheckpointerEngine,
    RetryPolicy,
    StepMeta,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    from_callable,
)


@pytest.fixture
async def engine(tmp_path):
    eng = PGCheckpointerEngine(
        f"sqlite+aiosqlite:///{(tmp_path / 'effects.db').as_posix()}"
    )
    await eng.init()
    try:
        yield eng
    finally:
        await eng.close()


@pytest.mark.asyncio
async def test_effect_identity_remains_stable_across_retry(engine):
    ids = []
    tokens = []
    count = 0

    async def act(ctx):
        nonlocal count
        count += 1
        ids.append(ctx.metadata["idempotency_key"])
        tokens.append(ctx.metadata["fencing_token"])
        if count == 1:
            return ActivityResult(success=False, error="injected transient error")
        return ActivityResult(success=True, output={"receipt": "ok"})

    wf = Workflow(
        id="effect-metadata", name="effect-metadata",
        steps=[WorkflowStep(
            meta=StepMeta(id="send", name="send"),
            activity=from_callable("send", act),
            retry_policy=RetryPolicy(
                max_attempts=2, initial_delay_s=0, max_delay_s=0,
            ),
        )],
    )
    result = await engine.start(wf, run_id="stable-effect-run")
    assert result.status == WorkflowStatus.COMPLETED
    assert len(ids) == 2
    assert ids[0] == ids[1]
    assert len(ids[0]) == 64
    assert tokens[0] == tokens[1] == 1


@pytest.mark.asyncio
async def test_inflight_cancel_does_not_get_overwritten_by_success(engine):
    started = asyncio.Event()
    release = asyncio.Event()

    async def act(ctx):
        started.set()
        await release.wait()
        return ActivityResult(success=True, output={"published": False})

    wf = Workflow(
        id="cancel-inflight", name="cancel-inflight",
        steps=[WorkflowStep(
            meta=StepMeta(id="work", name="work"),
            activity=from_callable("work", act),
        )],
    )
    running = asyncio.create_task(engine.start(wf, run_id="cancel-inflight-run"))
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        await engine.cancel("cancel-inflight-run", "user cancelled")
    finally:
        release.set()

    result = await asyncio.wait_for(running, timeout=10)
    assert result.status == WorkflowStatus.CANCELLED
    assert await engine.get_status("cancel-inflight-run") == WorkflowStatus.CANCELLED
