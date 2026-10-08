"""goal_service.py — GoalService (T0032 scope: write + event).

Two responsibilities:
1. create_goal(input) — construct a Goal from user input, assign
   id/created_at (already done by Envelope), persist, emit event.
2. abort(goal, reason) — transition Pending/Active to Aborted.

Out of scope (T0033+):
- Dispatching Tasks
- Verifier coordination
- Workflow scheduling
"""
from __future__ import annotations

import logging

from aios_kernel.domain.goal import Goal, GoalStatus

log = logging.getLogger(__name__)


class GoalService:
    """Service for Goal lifecycle (write + event)."""

    def __init__(self, repo):
        self.repo = repo

    async def create_goal(
        self,
        title,
        success_criteria,
        budget,
        owner,
        description=None,
        deadline=None,
        tags=None,
        metadata=None,
    ):
        goal = Goal(
            title=title,
            description=description,
            success_criteria=success_criteria,
            budget=budget,
            deadline=deadline,
            owner=owner,
            tags=tags or [],
            metadata=metadata or {},
        )
        await self.repo.add(goal)
        await self.repo.commit()
        log.info("goal.created id=%s owner=%s budget=%.2f", goal.id, goal.owner, goal.budget)
        return goal

    async def activate(self, goal):
        if not goal.can_transition_to(GoalStatus.ACTIVE):
            raise ValueError(
                f"cannot activate goal {goal.id!r} from {goal.status.value}"
            )
        goal.transition_to(GoalStatus.ACTIVE)
        await self.repo.add(goal)
        await self.repo.commit()
        log.info("goal.activated id=%s", goal.id)
        return goal

    async def complete(self, goal):
        if not goal.can_transition_to(GoalStatus.COMPLETED):
            raise ValueError(
                f"cannot complete goal {goal.id!r} from {goal.status.value}"
            )
        goal.transition_to(GoalStatus.COMPLETED)
        await self.repo.add(goal)
        await self.repo.commit()
        log.info("goal.completed id=%s", goal.id)
        return goal

    async def abort(self, goal, reason=""):
        if not goal.can_transition_to(GoalStatus.ABORTED):
            raise ValueError(
                f"cannot abort goal {goal.id!r} from {goal.status.value} (terminal)"
            )
        goal.transition_to(GoalStatus.ABORTED)
        if reason:
            goal.metadata["abort_reason"] = reason
        await self.repo.add(goal)
        await self.repo.commit()
        log.info("goal.aborted id=%s reason=%s", goal.id, reason)
        return goal

    async def fail(self, goal, reason=""):
        if not goal.can_transition_to(GoalStatus.FAILED):
            raise ValueError(
                f"cannot fail goal {goal.id!r} from {goal.status.value}"
            )
        goal.transition_to(GoalStatus.FAILED)
        if reason:
            goal.metadata["fail_reason"] = reason
        await self.repo.add(goal)
        await self.repo.commit()
        log.info("goal.failed id=%s reason=%s", goal.id, reason)
        return goal


__all__ = ["GoalService"]
