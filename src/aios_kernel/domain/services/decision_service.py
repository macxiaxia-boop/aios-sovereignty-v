"""decision_service.py — DecisionAudit service (Phase F F003).

Thin service layer that records and retrieves DecisionAudit rows.
Exposes five methods (per F003 §Scope):

    record(...)                 -> create a new audit row (PENDING)
    update_outcome(audit, ...)  -> write outcome back; touches updated_at
    get_by_goal(goal_id)        -> chain of audits for a goal
    get_by_actor(actor)         -> per-actor history (with limit)
    get_pending_outcomes()      -> all PENDING rows waiting for executor

The service is intentionally stateless beyond the injected Repository
— all real logic lives on the DecisionAudit Pydantic model. This mirrors
the GoalService / TaskService pattern.
"""
from __future__ import annotations

import logging
from typing import Any

from aios_kernel.domain.decision import DecisionActor, DecisionAudit, DecisionOutcome
from aios_kernel.domain.services.repository import Repository

log = logging.getLogger(__name__)


class DecisionService:
    """DecisionAudit write + retrieve API."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------
    # record / update
    # ------------------------------------------------------------------

    async def record(
        self,
        goal_id: str,
        actor: DecisionActor | str,
        rationale: str,
        chosen: str,
        alternatives: list[str] | None = None,
        confidence: float = 1.0,
        tags: list[str] | None = None,
        outcome: DecisionOutcome | str = DecisionOutcome.PENDING,
        outcome_detail: str | None = None,
    ) -> DecisionAudit:
        """Create a new audit row.

        Accepts both enum members and plain strings for actor/outcome
        (defensive — call code can use the enum or just the value). The
        returned DecisionAudit is already persisted and has its Pydantic
        ``id`` / ``created_at`` / ``updated_at`` populated.
        """
        actor_val = actor.value if hasattr(actor, "value") else str(actor)
        outcome_val = outcome.value if hasattr(outcome, "value") else str(outcome)
        audit = DecisionAudit(
            goal_id=goal_id,
            actor=DecisionActor(actor_val),
            rationale=rationale,
            chosen=chosen,
            alternatives=list(alternatives or []),
            confidence=float(confidence),
            tags=list(tags or []),
            outcome=DecisionOutcome(outcome_val),
            outcome_detail=outcome_detail,
        )
        await self.repo.add(audit)
        await self.repo.commit()
        log.info(
            "decision.recorded id=%s actor=%s goal_id=%s chosen=%s",
            audit.id,
            actor_val,
            goal_id,
            chosen,
        )
        return audit

    async def update_outcome(
        self,
        audit: DecisionAudit,
        outcome: DecisionOutcome | str | None = None,
        detail: str | None = None,
    ) -> DecisionAudit:
        """Persist the executor's outcome.

        Either ``outcome`` or ``detail`` (or both) must be supplied.
        When ``outcome`` is None, the existing ``audit.outcome`` is kept;
        this is the "executor only knows the detail" case (rare — most
        callers should pass outcome=).
        """
        if outcome is None and detail is None:
            raise ValueError("update_outcome requires outcome and/or detail")
        if outcome is not None:
            outcome_val = outcome.value if hasattr(outcome, "value") else str(outcome)
            audit.outcome = DecisionOutcome(outcome_val)
        if detail is not None:
            audit.outcome_detail = detail
        audit.touch()
        await self.repo.add(audit)
        await self.repo.commit()
        log.info(
            "decision.outcome_updated id=%s outcome=%s",
            audit.id,
            audit.outcome.value,
        )
        return audit

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    async def get_by_goal(self, goal_id: str) -> list[DecisionAudit]:
        """All audits tied to a single goal, oldest first."""
        from aios_kernel.domain.decision import DecisionAudit as _DA

        rows = await self.repo.find(_DA, goal_id=goal_id)
        # InMemoryRepository returns Pydantic rows; SQL impl returns ORM
        # rows. Normalise to Pydantic for callers.
        normalised = []
        for row in rows:
            if isinstance(row, DecisionAudit):
                normalised.append(row)
            else:
                normalised.append(_decision_from_orm(row))
        # Sort by created_at for stable presentation.
        normalised.sort(key=lambda a: a.created_at)
        return normalised

    async def get_by_actor(
        self, actor: DecisionActor | str, limit: int = 100
    ) -> list[DecisionAudit]:
        """Per-actor audit history, newest first (subject to limit)."""
        from aios_kernel.domain.decision import DecisionAudit as _DA

        actor_val = actor.value if hasattr(actor, "value") else str(actor)
        rows = await self.repo.find(_DA, actor=actor_val, limit=limit)
        normalised = []
        for row in rows:
            if isinstance(row, DecisionAudit):
                normalised.append(row)
            else:
                normalised.append(_decision_from_orm(row))
        normalised.sort(key=lambda a: a.created_at, reverse=True)
        return normalised

    async def get_pending_outcomes(self) -> list[DecisionAudit]:
        """All PENDING rows that still need an executor stamp."""
        from aios_kernel.domain.decision import DecisionAudit as _DA

        rows = await self.repo.find(_DA, outcome=DecisionOutcome.PENDING.value)
        normalised = []
        for row in rows:
            if isinstance(row, DecisionAudit):
                normalised.append(row)
            else:
                normalised.append(_decision_from_orm(row))
        normalised.sort(key=lambda a: a.created_at)
        return normalised

    # ------------------------------------------------------------------
    # utility
    # ------------------------------------------------------------------

    async def count_by_goal(self, goal_id: str) -> int:
        """Number of audits tied to a goal (for guard checks)."""
        rows = await self.get_by_goal(goal_id)
        return len(rows)


def _decision_from_orm(o: Any) -> DecisionAudit:
    """Build a DecisionAudit from an ORM row (kept here so the service is
    self-contained for the SQL path; avoids leaking ORM types upward).
    """
    from aios_kernel.domain.decision import DecisionActor, DecisionOutcome

    return DecisionAudit(
        id=o.id,
        goal_id=o.goal_id,
        actor=DecisionActor(o.actor),
        rationale=o.rationale,
        alternatives=list(o.alternatives or []),
        chosen=o.chosen,
        outcome=DecisionOutcome(o.outcome),
        outcome_detail=o.outcome_detail,
        confidence=float(o.confidence),
        tags=list(o.tags or []),
        schema_version=getattr(o, "schema_version", 1),
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


__all__ = ["DecisionService"]