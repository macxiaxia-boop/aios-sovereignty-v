"""test_plan_versioning.py - Plan v1..v5 chain (T0030 §2 判据 3).

Validates the auto-increment behavior of PlanService.create_version() and
the in-place Plan.bump_version() helper. The 5-version chain is the
acceptance test for the spec.
"""
from __future__ import annotations

import pytest

from aios_kernel.domain import Dependency, DependencyKind, Plan, PlanStep, StepType
from aios_kernel.domain.services import PlanService
from aios_kernel.domain.services.repository import InMemoryRepository


def _step(name, plan_id="", depends_on=None):
    return PlanStep(
        plan_id=plan_id,
        name=name,
        kind=StepType.TASK,
        depends_on=list(depends_on or []),
    )


# 1. Initial Plan starts at version 1, is_active=True
def test_plan_v1_initial():
    repo = InMemoryRepository()
    p = Plan(goal_id="g-1", version=1, is_active=True)
    assert p.version == 1
    assert p.is_active is True


# 2. bump_version increments and marks active
def test_bump_version_increments():
    p = Plan(goal_id="g-1", version=1, is_active=False)
    p.bump_version()
    assert p.version == 2
    assert p.is_active is True
    p.bump_version()
    assert p.version == 3


# 3. PlanService.create_version chain v1..v5
@pytest.mark.asyncio
async def test_plan_service_versions_v1_to_v5():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    p1 = await ps.create_plan(goal_id="g-1", steps=[_step("s1")], title="v1")
    assert p1.version == 1
    assert p1.is_active is True

    p2 = await ps.create_version(previous=p1, steps=[_step("s2")])
    assert p2.version == 2
    assert p2.parent_version == 1
    assert p1.is_active is False  # previous is deactivated
    assert p2.is_active is True

    p3 = await ps.create_version(previous=p2, steps=[_step("s3")])
    assert p3.version == 3
    assert p3.parent_version == 2

    p4 = await ps.create_version(previous=p3, steps=[_step("s4")])
    assert p4.version == 4

    p5 = await ps.create_version(previous=p4, steps=[_step("s5")])
    assert p5.version == 5
    assert p5.parent_version == 4

    # Only the last one is active
    for p in (p1, p2, p3, p4):
        assert p.is_active is False
    assert p5.is_active is True


# 4. Active plan for goal returns highest version
@pytest.mark.asyncio
async def test_get_active_for_goal_highest_version():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    p1 = await ps.create_plan(goal_id="g-1", steps=[_step("s1")])
    p2 = await ps.create_version(previous=p1, steps=[_step("s2")])
    p3 = await ps.create_version(previous=p2, steps=[_step("s3")])
    active = await ps.get_active_for_goal("g-1")
    assert active is p3
    assert active.version == 3


# 5. Step cannot depend on itself
def test_planstep_self_dep_rejected():
    s = _step("self")
    s.depends_on = [s.id]
    with pytest.raises(ValueError, match="cannot depend on itself"):
        PlanStep.model_validate(s.model_dump())


# 6. Dependency cannot have from_step == to_step
def test_dependency_self_edge_rejected():
    d = Dependency(plan_id="p1", from_step_id="x", to_step_id="x")
    with pytest.raises(ValueError, match="from_step_id == to_step_id"):
        Dependency.model_validate(d.model_dump())


# 7. add_step rejects duplicate
def test_add_step_duplicate_rejected():
    p = Plan(goal_id="g-1")
    s = _step("only")
    p.add_step(s)
    with pytest.raises(ValueError, match="already in plan"):
        p.add_step(s)


# 8. add_dependency references unknown step raises
def test_add_dependency_unknown_step():
    p = Plan(goal_id="g-1")
    s = _step("known")
    p.add_step(s)
    d = Dependency(plan_id=p.id, from_step_id=s.id, to_step_id="ghost")
    with pytest.raises(ValueError, match="references unknown step"):
        p.add_dependency(d)


# 9. steps are rebound to plan id
@pytest.mark.asyncio
async def test_create_plan_rebinds_step_plan_id():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    s = _step("alone", plan_id="wrong-id")
    p = await ps.create_plan(goal_id="g-1", steps=[s])
    assert all(step.plan_id == p.id for step in p.steps)


# 10. JSON schema export works
def test_plan_json_schema():
    p = Plan(goal_id="g-1")
    schema = p.model_json_schema()
    assert "properties" in schema
    assert "version" in schema["properties"]
    assert "steps" in schema["properties"]
    assert "is_active" in schema["properties"]
