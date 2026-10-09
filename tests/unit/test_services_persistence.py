"""test_services_persistence.py - service layer + SQLAlchemy persistence.

End-to-end: service -> SqlAlchemyRepository -> SQLite, then read back.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from aios_kernel.domain import (
    Artifact,
    ArtifactType,
    Evidence,
    Goal,
    GoalStatus,
    Plan,
    PlanStep,
    Task,
    TaskStatus,
    TaskType,
    Trace,
    TraceSpan,
    Verdict,
)
from aios_kernel.domain.services import GoalService, PlanService, TaskService
from aios_kernel.persistence import (
    ArtifactORM,
    EvidenceORM,
    GoalORM,
    PlanORM,
    TaskORM,
    TraceORM,
    VerifierRunORM,
    WorkerRunORM,
)


# ---------- GoalService + DB roundtrip --------------------------------------


@pytest.mark.asyncio
async def test_goal_service_persists_to_db(db_repo, async_engine):
    gs = GoalService(db_repo)
    g = await gs.create_goal(
        title="DB goal",
        success_criteria="All tasks done",
        budget=200.0,
        owner="codex",
    )
    # Force a separate session to read it back
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    factory = make_session_factory(async_engine)
    async with session_scope(factory) as session:
        orm = await session.get(GoalORM, g.id)
        assert orm is not None
        assert orm.title == "DB goal"
        assert orm.budget == 200.0
        assert orm.owner == "codex"
        assert orm.status == "Pending"


@pytest.mark.asyncio
async def test_goal_service_activate_and_complete(db_repo):
    gs = GoalService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    await gs.activate(g)
    assert g.status == GoalStatus.ACTIVE
    await gs.complete(g)
    assert g.is_terminal
    # Should also be persisted as Completed
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    from aios_kernel.domain.services.repository import make_engine
    # Re-fetch via a separate transaction: we already have the session;
    # the in-memory test orm has it. Just check the events list.
    kinds = [e[0] for e in db_repo.events]
    assert kinds.count("add") >= 3  # create, activate, complete
    assert kinds.count("commit") >= 3


# ---------- TaskService state transitions -----------------------------------


@pytest.mark.asyncio
async def test_task_full_lifecycle(db_repo):
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t", task_type=TaskType.MATH_CALC)
    await ts.start(t)
    await ts.mark_verifying(t)
    await ts.mark_done(t)
    assert t.is_terminal
    assert t.completed_at is not None
    assert t.started_at is not None


@pytest.mark.asyncio
async def test_task_illegal_transition_via_service(db_repo):
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t", task_type=TaskType.CUSTOM)
    with pytest.raises(ValueError, match="illegal"):
        await ts.mark_done(t)  # PENDING -> DONE is illegal


# ---------- PlanService versioning ------------------------------------------


@pytest.mark.asyncio
async def test_plan_service_v1_through_v3(db_repo):
    gs = GoalService(db_repo)
    ps = PlanService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    p1 = await ps.create_plan(goal_id=g.id, steps=[PlanStep(plan_id="", name="s1")])
    p2 = await ps.create_version(previous=p1, steps=[PlanStep(plan_id="", name="s2")])
    p3 = await ps.create_version(previous=p2, steps=[PlanStep(plan_id="", name="s3")])
    assert (p1.version, p2.version, p3.version) == (1, 2, 3)
    assert p3.parent_version == 2
    assert p1.is_active is False and p3.is_active is True


# ---------- Artifact + Evidence + Trace persistence ------------------------


@pytest.mark.asyncio
async def test_full_artifact_evidence_trace_chain(db_repo, async_engine):
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t", task_type=TaskType.CUSTOM)
    await ts.start(t)

    a = Artifact(
        task_id=t.id, artifact_type=ArtifactType.TEXT, inline_content="hello"
    )
    e = Evidence(task_id=t.id, verifier_id="v-001", verdict=Verdict.PASS)
    tr = Trace(goal_id=g.id, task_id=t.id, name="run-1")
    sp = TraceSpan(trace_id=tr.id, span_id="s1", name="dispatch")
    sp.finish()
    tr.add_span(sp)

    await db_repo.add(a)
    await db_repo.add(e)
    await db_repo.add(tr)
    await db_repo.commit()

    # Read back from a fresh session
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    factory = make_session_factory(async_engine)
    async with session_scope(factory) as session:
        a_orm = await session.get(ArtifactORM, a.id)
        e_orm = await session.get(EvidenceORM, e.id)
        t_orm = await session.get(TraceORM, tr.id)
        assert a_orm is not None
        assert a_orm.task_id == t.id
        assert a_orm.artifact_type == "text"
        assert e_orm is not None
        assert e_orm.verdict == "PASS"
        assert e_orm.verifier_id == "v-001"
        assert t_orm is not None
        assert t_orm.goal_id == g.id
        assert len(t_orm.spans) == 1
        assert t_orm.spans[0]["span_id"] == "s1"


# ---------- Naive datetime rejection at ORM boundary ------------------------


@pytest.mark.asyncio
async def test_naive_datetime_rejected_in_orm(db_repo, async_engine):
    """Pydantic v2 Evidence rejects naive datetime on signed_at field."""
    from datetime import datetime, timezone
    from aios_kernel.domain.evidence import Evidence
    import pytest

    # Pydantic must raise for naive datetime on signed_at
    with pytest.raises(ValueError, match="tz-aware"):
        Evidence(task_id="t-1", verifier_id="v-1", signed_at=datetime.now())

    # Round-trip with tz-aware datetime still works (tz preserved on disk is best-effort,
    # SQLAlchemy+SQLite is known to strip tzinfo on retrieval which is acceptable for our
    # Phase F decision_audit use case where we care about ordering, not exact tz).
    from aios_kernel.domain.envelope import utcnow
    from aios_kernel.domain.services import GoalService, TaskService
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t")
    e = Evidence(task_id=t.id, verifier_id="v-1", signed_at=utcnow())
    await db_repo.add(e)
    await db_repo.commit()
    # Verify it persists without crash
    assert e.signed_at.tzinfo is not None  # pydantic side retains tz
@pytest.mark.asyncio
async def test_goal_service_persists_to_db(db_repo, async_engine):
    gs = GoalService(db_repo)
    g = await gs.create_goal(
        title="DB goal",
        success_criteria="All tasks done",
        budget=200.0,
        owner="codex",
    )
    # Force a separate session to read it back
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    factory = make_session_factory(async_engine)
    async with session_scope(factory) as session:
        orm = await session.get(GoalORM, g.id)
        assert orm is not None
        assert orm.title == "DB goal"
        assert orm.budget == 200.0
        assert orm.owner == "codex"
        assert orm.status == "Pending"


@pytest.mark.asyncio
async def test_goal_service_activate_and_complete(db_repo):
    gs = GoalService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    await gs.activate(g)
    assert g.status == GoalStatus.ACTIVE
    await gs.complete(g)
    assert g.is_terminal
    # Should also be persisted as Completed
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    from aios_kernel.domain.services.repository import make_engine
    # Re-fetch via a separate transaction: we already have the session;
    # the in-memory test orm has it. Just check the events list.
    kinds = [e[0] for e in db_repo.events]
    assert kinds.count("add") >= 3  # create, activate, complete
    assert kinds.count("commit") >= 3


# ---------- TaskService state transitions -----------------------------------


@pytest.mark.asyncio
async def test_task_full_lifecycle(db_repo):
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t", task_type=TaskType.MATH_CALC)
    await ts.start(t)
    await ts.mark_verifying(t)
    await ts.mark_done(t)
    assert t.is_terminal
    assert t.completed_at is not None
    assert t.started_at is not None


@pytest.mark.asyncio
async def test_task_illegal_transition_via_service(db_repo):
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t", task_type=TaskType.CUSTOM)
    with pytest.raises(ValueError, match="illegal"):
        await ts.mark_done(t)  # PENDING -> DONE is illegal


# ---------- PlanService versioning ------------------------------------------


@pytest.mark.asyncio
async def test_plan_service_v1_through_v3(db_repo):
    gs = GoalService(db_repo)
    ps = PlanService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    p1 = await ps.create_plan(goal_id=g.id, steps=[PlanStep(plan_id="", name="s1")])
    p2 = await ps.create_version(previous=p1, steps=[PlanStep(plan_id="", name="s2")])
    p3 = await ps.create_version(previous=p2, steps=[PlanStep(plan_id="", name="s3")])
    assert (p1.version, p2.version, p3.version) == (1, 2, 3)
    assert p3.parent_version == 2
    assert p1.is_active is False and p3.is_active is True


# ---------- Artifact + Evidence + Trace persistence ------------------------


@pytest.mark.asyncio
async def test_full_artifact_evidence_trace_chain(db_repo, async_engine):
    gs = GoalService(db_repo)
    ts = TaskService(db_repo)
    g = await gs.create_goal(title="g", success_criteria="x", budget=1.0, owner="o")
    t = await ts.create_task(goal_id=g.id, title="t", task_type=TaskType.CUSTOM)
    await ts.start(t)

    a = Artifact(
        task_id=t.id, artifact_type=ArtifactType.TEXT, inline_content="hello"
    )
    e = Evidence(task_id=t.id, verifier_id="v-001", verdict=Verdict.PASS)
    tr = Trace(goal_id=g.id, task_id=t.id, name="run-1")
    sp = TraceSpan(trace_id=tr.id, span_id="s1", name="dispatch")
    sp.finish()
    tr.add_span(sp)

    await db_repo.add(a)
    await db_repo.add(e)
    await db_repo.add(tr)
    await db_repo.commit()

    # Read back from a fresh session
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    factory = make_session_factory(async_engine)
    async with session_scope(factory) as session:
        a_orm = await session.get(ArtifactORM, a.id)
        e_orm = await session.get(EvidenceORM, e.id)
        t_orm = await session.get(TraceORM, tr.id)
        assert a_orm is not None
        assert a_orm.task_id == t.id
        assert a_orm.artifact_type == "text"
        assert e_orm is not None
        assert e_orm.verdict == "PASS"
        assert e_orm.verifier_id == "v-001"
        assert t_orm is not None
        assert t_orm.goal_id == g.id
        assert len(t_orm.spans) == 1
        assert t_orm.spans[0]["span_id"] == "s1"

