"""goal.py — Goal aggregate root (Phase A T0030 §4).

A Goal is the top-level unit of intent. Each Goal has success criteria,
budget, optional deadline, and an owner (agent identifier). Multiple Tasks
inside a Goal all contribute to the same success_criteria.

Status machine: Pending -> Active -> Completed | Failed | Aborted.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope


class GoalStatus(str, Enum):
    """Lifecycle states for a Goal.

    Order reflects forward progression; reverse transitions are not allowed
    (use Aborted from any state if you need to cancel).
    """

    PENDING = "Pending"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABORTED = "Aborted"

    @classmethod
    def terminal(cls):
        return {cls.COMPLETED, cls.FAILED, cls.ABORTED}


# Allowed forward transitions (FROM -> set of valid TO).
GOAL_TRANSITIONS: dict = {
    GoalStatus.PENDING: {GoalStatus.ACTIVE, GoalStatus.ABORTED, GoalStatus.FAILED},
    GoalStatus.ACTIVE: {GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ABORTED},
    GoalStatus.COMPLETED: set(),
    GoalStatus.FAILED: set(),
    GoalStatus.ABORTED: set(),
}


class Goal(Envelope):
    """A Goal represents the high-level intent of a session.

    Fields beyond the Envelope base:
    - title: human-readable summary
    - description: optional longer rationale
    - success_criteria: machine-checkable success statement
    - budget: spending cap in CNY (¥), enforced by T0034/T0036
    - deadline: optional hard deadline (tz-aware UTC)
    - owner: agent identifier (e.g. "codex", "claudecode", "human:user")
    - status: lifecycle state (see GoalStatus)
    - tags: free-form labels for grouping
    - plan_ids: list of Plan ids attached to this goal (forward ref; T0032 ORM
      enforces FK; we keep the list denormalized for fast read).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    title: str = Field(..., min_length=1, max_length=200, description="Short goal title.")
    description: str | None = Field(
        default=None, max_length=2000, description="Longer rationale (Markdown ok)."
    )
    success_criteria: str = Field(
        ..., min_length=1, description="Machine-checkable success statement."
    )
    budget: float = Field(..., ge=0.0, description="Spending cap in CNY (¥); must be >= 0.")
    deadline: datetime | None = Field(
        default=None, description="Optional hard deadline (tz-aware UTC)."
    )
    owner: str = Field(..., min_length=1, description="Agent/user identifier owning this goal.")
    status: GoalStatus = Field(default=GoalStatus.PENDING, description="Lifecycle state.")
    tags: list = Field(default_factory=list, description="Free-form labels.")
    plan_ids: list = Field(
        default_factory=list, description="Plan ids attached to this Goal (denormalized)."
    )
    metadata: dict = Field(
        default_factory=dict, description="Free-form structured metadata."
    )

    @field_validator("deadline")
    @classmethod
    def _deadline_tz(cls, value):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("deadline must be tz-aware (use envelope.utcnow()-style)")
        return value.astimezone(UTC)

    # ---------- business methods -------------------------------------------

    def can_transition_to(self, new_status):
        return new_status in GOAL_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"illegal Goal status transition: {self.status.value} -> {new_status.value}"
            )
        self.status = new_status
        self.touch()
        return self

    @property
    def is_terminal(self):
        return self.status in GoalStatus.terminal()

    def add_plan(self, plan_id):
        if plan_id not in self.plan_ids:
            self.plan_ids.append(plan_id)
            self.touch()

    def remaining_budget(self, spent):
        return max(0.0, float(self.budget) - float(spent))


__all__ = ["Goal", "GoalStatus", "GOAL_TRANSITIONS"]
