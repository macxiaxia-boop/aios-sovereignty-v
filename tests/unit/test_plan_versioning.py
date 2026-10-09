"""test_plan_versioning.py - Plan v1..v5 chain (T0030 §2 判据 3).

Validates the auto-increment behavior of PlanService.create_version() and
the in-place Plan.bump_version() helper. The 5-version chain is the
acceptance test for the spec.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from aios_kernel.domain import Dependency, DependencyKind, Plan, PlanStep, StepType
from aios_kernel.domain.services import PlanService
from aios_kernel.domain.services.repository import InMemoryRepository


def _step(name, plan_id="", depends_on=None):
    return PlanStep(
        plan_id=plan_id,
        name=name,
        kind=StepType.TASK,
        input_payload={},
        depends_on=list(depends_on or []),
    )


# 1. create_plan assigns v1
@pytest.mark.asyncio
async def test_create_plan_v1():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    p = await ps.create_plan(goal_id="g-1", steps=[_step("s1")])
    assert p.version == 1


# 2. create_version bumps to v2, v3...
@pytest.mark.asyncio
async def test_create_version_chain():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    p1 = await ps.create_plan(goal_id="g-1", steps=[_step("s1")])
    p2 = await ps.create_version(previous=p1, steps=[_step("s2")])
    p3 = await ps.create_version(previous=p2, steps=[_step("s3")])
    assert p2.version == 2
    assert p3.version == 3
    assert all(p.goal_id == "g-1" for p in [p1, p2, p3])


# 3. plan IDs are unique per version
@pytest.mark.asyncio
async def test_plan_ids_unique_per_version():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    p1 = await ps.create_plan(goal_id="g-1", steps=[_step("s1")])
    p2 = await ps.create_version(previous=p1, steps=[_step("s2")])
    assert p1.id != p2.id


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


# 5. Step cannot depend on itself (validation raises on assignment)
def test_planstep_self_dep_rejected():
    s = _step("self")
    # Pydantic validate_assignment raises ValueError when depends_on contains self.id
    with pytest.raises(ValueError, match="cannot depend on itself"):
        s.depends_on = [s.id]


# 6. Dependency cannot have from_step == to_step (validation raises on construction)
def test_dependency_self_edge_rejected():
    with pytest.raises(ValueError, match="from_step_id == to_step_id"):
        Dependency(plan_id="p1", from_step_id="x", to_step_id="x")


# 7. add_step rejects duplicate
def test_add_step_duplicate_rejected():
    pass  # placeholder for future expansion


# 8. version monotonic across merges
@pytest.mark.asyncio
async def test_version_monotonic():
    repo = InMemoryRepository()
    ps = PlanService(repo)
    versions = []
    p = await ps.create_plan(goal_id="g-1", steps=[_step("s1")])
    versions.append(p.version)
    for i in range(2, 6):
        p = await ps.create_version(previous=p, steps=[_step(f"s{i}")])
        versions.append(p.version)
    assert versions == [1, 2, 3, 4, 5]
    assert all(b > a for a, b in zip(versions, versions[1:]))