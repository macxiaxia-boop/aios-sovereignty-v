"""plan_service.py — PlanService (T0032 scope: write + event).

Responsibilities:
- create_plan: build a Plan v1 for a Goal, persist.
- create_version: fork a new Plan with auto-incremented version, mark
  the old one inactive, persist, return the new plan.
- add_step: convenience for plan authors.
- rollback_to: revert a Goal plan to an earlier version.
"""
from __future__ import annotations

import logging

from aios_kernel.domain.plan import Plan

log = logging.getLogger(__name__)


class PlanService:
    def __init__(self, repo):
        self.repo = repo

    async def create_plan(
        self,
        goal_id,
        steps,
        title="",
        description=None,
        created_by="system",
        metadata=None,
    ):
        plan = Plan(
            goal_id=goal_id,
            version=1,
            is_active=True,
            title=title,
            description=description,
            created_by=created_by,
            metadata=metadata or {},
        )
        for step in steps:
            plan.add_step(step)
        await self.repo.add(plan)
        await self.repo.commit()
        log.info("plan.created id=%s goal_id=%s version=1 steps=%d", plan.id, goal_id, len(steps))
        return plan

    async def create_version(
        self,
        previous,
        steps,
        title="",
        description=None,
        created_by="system",
        rollback_to=None,
        metadata=None,
    ):
        previous.mark_inactive()
        await self.repo.add(previous)
        await self.repo.commit()

        new = Plan(
            goal_id=previous.goal_id,
            version=previous.version + 1,
            is_active=True,
            parent_version=previous.version,
            title=title or previous.title,
            description=description or previous.description,
            created_by=created_by,
            rollback_to=rollback_to,
            metadata=metadata or {},
        )
        for step in steps:
            new.add_step(step)
        await self.repo.add(new)
        await self.repo.commit()
        log.info(
            "plan.bump id=%s goal_id=%s version=%d parent_version=%d steps=%d",
            new.id, new.goal_id, new.version, new.parent_version, len(new.steps),
        )
        return new

    async def add_step(self, plan, step):
        plan.add_step(step)
        await self.repo.add(plan)
        await self.repo.commit()
        return plan

    async def add_dependency(self, plan, dep):
        plan.add_dependency(dep)
        await self.repo.add(plan)
        await self.repo.commit()
        return plan

    async def get_active_for_goal(self, goal_id):
        plans = self.repo.all(Plan) if hasattr(self.repo, "all") else []
        active = [p for p in plans if p.goal_id == goal_id and p.is_active]
        if not active:
            return None
        return max(active, key=lambda p: p.version)


__all__ = ["PlanService"]
