"""P7 real WorkflowEngine external-effect safety.

Tests use fake providers only. No social publishing, payments, or credentials.
The journal blocks unknown results until an independently verified receipt
is supplied by an authorized orchestrator.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from aios_kernel.workflows import (
    ActivityResult,
    PGCheckpointerEngine,
    StepMeta,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    from_callable,
)
from aios_kernel.workflows.persistence import WorkflowEffectRow


@pytest.fixture
async def eng(tmp_path):
    e = PGCheckpointerEngine(
        f"sqlite+aiosqlite:///{(tmp_path / 'effects.db').as_posix()}"
    )
    await e.init()
    try:
        yield e
    finally:
        await e.close()


def _external(fn):
    return Workflow(
        id="external-publish", name="external-publish",
        steps=[WorkflowStep(
            meta=StepMeta(id="publish", name="publish"),
            activity=from_callable("publish", fn),
            external_effect=True,
        )],
    )


@pytest.mark.asyncio
async def test_uncertain_remote_response_blocks_without_retry(eng):
    calls = []
    async def publish(ctx):
        calls.append(ctx.metadata["idempotency_key"])
        raise TimeoutError("response lost after request was sent")

    wf = _external(publish)
    result = await eng.start(wf, run_id="unknown-remote-result")
    assert result.status == WorkflowStatus.BLOCKED
    assert len(calls) == 1
    again = await eng.resume(wf, result.run_id)
    assert again.status == WorkflowStatus.BLOCKED
    assert calls == [calls[0]]  # no blind resend
    async with eng._session_factory() as session:
        rows = (await session.execute(select(WorkflowEffectRow))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "uncertain"


@pytest.mark.asyncio
async def test_independent_reconciliation_resumes_without_republishing(eng):
    calls = []
    async def publish(ctx):
        calls.append(ctx.run_id)
        raise TimeoutError("no receipt")

    wf = _external(publish)
    blocked = await eng.start(wf, run_id="reconcile-run")
    assert blocked.status == WorkflowStatus.BLOCKED
    receipt = {
        "remote_receipt": {"provider": "mock-platform", "resource_id": "p123"},
        "output_ref": "asset-sha256-reference",
    }
    await eng.confirm_external_effect(
        run_id="reconcile-run", step_id="publish",
        remote_output=receipt,
        verification_evidence="read-only remote resource lookup recorded in test",
    )
    done = await eng.resume(wf, "reconcile-run")
    assert done.status == WorkflowStatus.COMPLETED
    assert calls == ["reconcile-run"]
    assert done.output["steps"]["publish"] == receipt


@pytest.mark.asyncio
async def test_missing_receipt_does_not_count_success(eng):
    calls = []
    async def publish(ctx):
        calls.append(1)
        return ActivityResult(success=True, output={"message": "ok"})

    wf = _external(publish)
    done = await eng.start(wf, run_id="no-receipt")
    assert done.status == WorkflowStatus.BLOCKED
    assert calls == [1]
    again = await eng.resume(wf, "no-receipt")
    assert again.status == WorkflowStatus.BLOCKED
    assert calls == [1]


@pytest.mark.asyncio
async def test_valid_remote_receipt_completes_once(eng):
    keys = []
    async def publish(ctx):
        keys.append((ctx.metadata["idempotency_key"], ctx.metadata["fencing_token"]))
        return ActivityResult(
            success=True,
            output={"remote_receipt": {"provider": "mock", "resource_id": "post1"}},
        )

    wf = _external(publish)
    first = await eng.start(wf, run_id="one-remote-effect")
    assert first.status == WorkflowStatus.COMPLETED
    repeated = await eng.start(wf, run_id="one-remote-effect")
    assert repeated.status == WorkflowStatus.COMPLETED
    assert len(keys) == 1
    assert len(keys[0][0]) == 64
    assert keys[0][1] == 1


@pytest.mark.asyncio
async def test_reconciliation_must_supply_receipt_and_evidence(eng):
    async def publish(ctx):
        raise TimeoutError("unknown")

    wf = _external(publish)
    await eng.start(wf, run_id="no-fake-evidence")
    with pytest.raises(ValueError, match="receipt and evidence"):
        await eng.confirm_external_effect(
            run_id="no-fake-evidence",
            step_id="publish",
            remote_output={"remote_receipt": {}},
            verification_evidence="",
        )
