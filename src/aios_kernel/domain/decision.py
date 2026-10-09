"""decision.py — Decision Audit domain model (Phase F F003).

Each AIOS decision (route dispatch / GoalContract parse / failure merge /
intent interpretation / operator override) writes one DecisionAudit row,
forming a verifiable chain that answers: "who decided what, when, with what
rationale, with what outcome?". Without this audit log, multi-agent
governance is unobservable.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope, utcnow


class DecisionActor(str, Enum):
    """主体 who emitted the decision.

    Covers the multi-agent stack plus human / system override. ``SYSTEM`` is
    used for fully automatic rule-driven decisions (e.g. auto-retry, budget
    guardrail) where no human/agent authored the rationale.
    """

    CODEX = "codex"
    CLAUDECODE = "claudecode"
    HERMES = "hermes"
    OPENCLAW = "openclaw"
    HUMAN = "human"
    SYSTEM = "system"


class DecisionOutcome(str, Enum):
    """Execution outcome of the decision. Filled by executor (CC/worker).

    PENDING  = the decision was recorded but no executor has reported back yet.
    SUCCEEDED = the chosen action ran to completion.
    FAILED   = the chosen action ran but errored.
    BLOCKED  = the chosen action was vetoed by GoalGuard or another gate.
    """

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class DecisionAudit(Envelope):
    """One auditable decision row.

    Fields beyond the Envelope base:
    - goal_id: FK to goals.id — every decision is anchored to a Goal.
    - actor: who made the decision (DecisionActor enum).
    - rationale: 1+ sentence justification (mandatory; ``min_length=1``).
    - alternatives: list of considered but rejected options.
    - chosen: the option actually selected.
    - outcome: execution result (PENDING by default; executor updates).
    - outcome_detail: free-form detail when marking the outcome.
    - confidence: 0.0-1.0 confidence score (validator-enforced).
    - tags: free-form labels for grouping / filtering.

    Lifecycle:
    - record() in DecisionService creates one with PENDING.
    - mark_outcome() called by executor once the decision is realised.
    - update_outcome() in DecisionService persists the outcome back to DB.
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    goal_id: str = Field(
        ..., min_length=1, description="FK to goals.id; the decision's anchor."
    )
    actor: DecisionActor = Field(..., description="Decision subject (actor enum).")
    rationale: str = Field(
        ..., min_length=1, description="Justification; why this over alternatives."
    )
    alternatives: list[str] = Field(
        default_factory=list, description="Options considered but rejected."
    )
    chosen: str = Field(
        ..., min_length=1, description="The option finally selected."
    )
    outcome: DecisionOutcome = Field(
        default=DecisionOutcome.PENDING, description="Execution outcome."
    )
    outcome_detail: str | None = Field(
        default=None, description="Free-form detail set by executor."
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in [0.0, 1.0]."
    )
    tags: list[str] = Field(
        default_factory=list, description="Free-form labels for filtering."
    )

    @field_validator("confidence")
    @classmethod
    def _conf_range(cls, value):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {value}")
        return float(value)

    @field_validator("alternatives", "tags")
    @classmethod
    def _string_lists(cls, value):
        # Each entry must be a string (Pydantic-friendly coercion).
        return [str(v) for v in value]

    # ---------- business methods -------------------------------------------

    def mark_outcome(self, outcome: DecisionOutcome, detail: str | None = None):
        """CC / executor callback: stamp the execution result.

        ``touch()`` is called so ``updated_at`` moves forward, so the audit
        chain shows PENDING → SUCCEEDED/FAILED/BLOCKED over time.
        """
        self.outcome = outcome
        if detail:
            self.outcome_detail = detail
        self.touch()
        return self

    def add_alternative(self, alternative: str):
        """Idempotent helper used by callers who build the audit incrementally."""
        if alternative and alternative not in self.alternatives:
            self.alternatives.append(alternative)
            self.touch()

    def add_tag(self, tag: str):
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.touch()

    def __repr__(self):  # pragma: no cover - debug aid
        return (
            f"<DecisionAudit id={self.id[:8]}… "
            f"actor={self.actor.value} goal_id={self.goal_id[:8]}… "
            f"outcome={self.outcome.value} confidence={self.confidence:.2f}>"
        )


__all__ = ["DecisionActor", "DecisionOutcome", "DecisionAudit"]