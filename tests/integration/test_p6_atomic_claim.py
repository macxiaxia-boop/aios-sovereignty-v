"""Atomic first-submission gate: only the winner of INSERT may execute.

Database conflict handling is tested with SQLite and synthetic race-window
injection. Real PostgreSQL concurrent-process verification remains required.
"""
from __future__ import annotations

import pytest

import aios_kernel.workflows.engine as engine_module
from aios_kernel.workflows import (
    ActivityResult,
    PGCheckpointerEngine,
    StepMeta,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    from_callable,
)
from aios_kernel.workflows.persistence import insert_run


@pytest.fixture
async def engine(tmp_path):
    item = PGCheckpointerEngine(f"sqlite+aiosqlite:///{(tmp_path / 'claim.db').as_posix()}")
    await item.init()
    try:
        yield item
    finally:
        await item.close()


def _wf(calls):
    async def write(ctx):
        calls.append(ctx.run_id)
        return ActivityResult(success=True, output={"effect": "once"})
    return Workflow(
        id="atomic-first-claim",
        name="claim",
        steps=[WorkflowStep(
            meta=StepMeta(id="write", name="write"),
            activity=from_callable("write", write),
        )],
    )


@pytest.mark.asyncio
async def test_insert_run_returns_whether_insert_won(engine):
    async with engine._session_factory() as session:
        first = await insert_run(
            session, run_id="existing", workflow_id="atomic-first-claim",
            input_json={"a": 1},
        )
        await session.commit()
        second = await insert_run(
            session, run_id="existing", workflow_id="atomic-first-claim",
            input_json={"a": 1},
        )
        await session.commit()
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_loser_of_insert_conflict_does_not_run_activity(engine, monkeypatch):
    calls = []
    wf = _wf(calls)
    real_insert = engine_module.insert_run

    async def injected_conflict(session, **kwargs):
        # Simulate a competitor winning after our empty initial SELECT,
        # before our INSERT. The insert itself still commits a genuine row.
        assert await real_insert(session, **kwargs)
        return False

    monkeypatch.setattr(engine_module, "insert_run", injected_conflict)
    result = await engine.start(wf, run_id="race-window", input={"x": 1})
    assert result.status == WorkflowStatus.PENDING
    assert calls == []  # losing submission does not dispatch any activity

    monkeypatch.setattr(engine_module, "insert_run", real_insert)
    finished = await engine.resume(wf, "race-window")
    assert finished.status == WorkflowStatus.COMPLETED
    assert calls == ["race-window"]


@pytest.mark.asyncio
async def test_conflict_checks_input_even_when_initial_read_was_empty(engine, monkeypatch):
    calls = []
    wf = _wf(calls)
    real_insert = engine_module.insert_run

    async def injected_conflict(session, **kwargs):
        await real_insert(
            session, run_id=kwargs["run_id"],
            workflow_id=kwargs["workflow_id"],
            input_json={"original": 1},
        )
        return False

    monkeypatch.setattr(engine_module, "insert_run", injected_conflict)
    with pytest.raises(ValueError, match="different input"):
        await engine.start(wf, run_id="changed-after-read", input={"different": 1})
    assert calls == []


@pytest.mark.asyncio
async def test_explicit_replay_uses_persisted_snapshot_not_side_effect(engine):
    calls = []
    wf = _wf(calls)
    first = await engine.start(wf, run_id="no-duplicate-effect", input={"x": 1})
    second = await engine.start(wf, run_id="no-duplicate-effect", input={"x": 1})
    assert first.status == second.status == WorkflowStatus.COMPLETED
    assert calls == ["no-duplicate-effect"]
