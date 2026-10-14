"""P5 regression tests for actual AIOS workflow persistence and runtime semantics.

Run with: python -m pytest tests/integration/test_p5_workflow_integrity.py -q
These tests require dependencies from pyproject.toml, including aiosqlite.
Never use a production database to run them.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from aios_kernel.workflows import (
    ActivityResult,
    PGCheckpointerEngine,
    StepMeta,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    from_callable,
)
from aios_kernel.workflows.persistence import insert_run, write_checkpoint


def _workflow(workflow_id: str, action):
    return Workflow(
        id=workflow_id,
        name=workflow_id,
        steps=[WorkflowStep(
            meta=StepMeta(id="work", name="work"),
            activity=from_callable("work", action),
        )],
    )


@pytest.fixture
async def engine(tmp_path):
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'p5.db').as_posix()}"
    value = PGCheckpointerEngine(database_url)
    await value.init()
    try:
        yield value
    finally:
        await value.close()


@pytest.mark.asyncio
async def test_business_input_reaches_activity_and_result_survives_restart(engine):
    seen = []
    async def act(ctx):
        seen.append(ctx.input["workflow_input"])
        return ActivityResult(success=True, output={"artifact_id": "example-001"})
    wf = _workflow("p5-input", act)
    run = await engine.start(wf, run_id="p5-input-run", input={"goal": "fix pipeline"})
    assert run.status == WorkflowStatus.COMPLETED
    assert seen == [{"goal": "fix pipeline"}]
    assert run.output["steps"]["work"]["artifact_id"] == "example-001"
    snapshot = await engine.start(wf, run_id="p5-input-run", input={"goal": "fix pipeline"})
    assert snapshot.output == run.output
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_same_run_id_conflicting_input_fails_without_execution(engine):
    calls = []
    async def act(ctx):
        calls.append(1)
        return ActivityResult(success=True, output={})
    wf = _workflow("p5-idempotence", act)
    await engine.start(wf, run_id="p5-dedup", input={"text": "A"})
    with pytest.raises(ValueError, match="different input"):
        await engine.start(wf, run_id="p5-dedup", input={"text": "B"})
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_run_id_cannot_be_reused_by_different_workflow(engine):
    async def act(ctx):
        return ActivityResult(success=True, output={})
    a = _workflow("a", act)
    b = _workflow("b", act)
    await engine.start(a, run_id="same-id")
    with pytest.raises(ValueError, match="different workflow"):
        await engine.start(b, run_id="same-id")
    with pytest.raises(ValueError, match="workflow identity"):
        await engine.resume(b, "same-id")


@pytest.mark.asyncio
async def test_recover_running_only_recovers_matching_workflow(engine):
    calls = []
    async def act(ctx):
        calls.append(ctx.run_id)
        return ActivityResult(success=True, output={"run": ctx.run_id})
    a = _workflow("wf-A", act)
    b = _workflow("wf-B", act)
    async with engine._session_factory() as session:
        await insert_run(session, run_id="pending-A", workflow_id=a.id, input_json={})
        await insert_run(session, run_id="pending-B", workflow_id=b.id, input_json={})
        await session.commit()
    recovered = await engine.recover_running(a)
    assert [r.run_id for r in recovered] == ["pending-A"]
    assert calls == ["pending-A"]
    assert await engine.get_status("pending-B") == WorkflowStatus.PENDING


@pytest.mark.asyncio
async def test_failed_checkpoint_does_not_skip_work(engine):
    calls = []
    async def act(ctx):
        calls.append(ctx.run_id)
        return ActivityResult(success=True, output={"fixed": True})
    wf = _workflow("failed-checkpoint", act)
    async with engine._session_factory() as session:
        await insert_run(
            session, run_id="failed-cp-run",
            workflow_id=wf.id, input_json={"work": True},
        )
        await write_checkpoint(
            session, run_id="failed-cp-run", step_id="work",
            step_index=0, state_json={"error": "timeout"},
            attempt=1, status="failed",
        )
        await session.commit()
    result = await engine.resume(wf, "failed-cp-run")
    assert result.status == WorkflowStatus.COMPLETED
    assert result.output["steps"]["work"] == {"fixed": True}
    assert calls == ["failed-cp-run"]


class _RecordingSession:
    def __init__(self, dialect):
        self._dialect = dialect
        self.statement = None
    def get_bind(self):
        return SimpleNamespace(dialect=self._dialect)
    async def execute(self, statement):
        self.statement = statement
    async def flush(self):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
async def test_insert_compiles_with_backend_dialect(dialect):
    session = _RecordingSession(dialect)
    await insert_run(
        session, run_id="test-run", workflow_id="workflow",
        input_json={"goal": "test"},
    )
    compiled = str(session.statement.compile(dialect=dialect))
    assert "ON CONFLICT" in compiled
    assert "DO NOTHING" in compiled


@pytest.mark.asyncio
async def test_repeated_explicit_run_id_returns_snapshot_not_replay(engine):
    count = 0
    async def act(ctx):
        nonlocal count
        count += 1
        return ActivityResult(success=True, output={"count": count})
    wf = _workflow("no-replay", act)
    first = await engine.start(wf, run_id="stable-run", input={"task": 1})
    second = await engine.start(wf, run_id="stable-run", input={"task": 1})
    assert count == 1
    assert first.output == second.output
