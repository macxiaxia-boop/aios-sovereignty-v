"""trace.py — Trace + TraceSpan + EventType (Phase A T0030 §4 + §7).

Traces are append-only observability records. A TraceSpan is a unit
of work (a worker call, a verifier call, a state transition, etc.) and
Trace is a top-level grouping (e.g. per-Goal run).

The kernel writes traces on:
- Goal/Task/Plan state transitions
- Worker execute() start/end
- Verifier sign() events
- Workflow checkpoints (T0033)
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar

from pydantic import Field, field_validator, model_validator

from aios_kernel.domain.envelope import Envelope, utcnow


class EventType(str, Enum):
    """The 8 canonical event types a TraceSpan can carry."""

    GOAL_CREATED = "goal.created"
    GOAL_TRANSITION = "goal.transition"
    TASK_DISPATCH = "task.dispatch"
    TASK_TRANSITION = "task.transition"
    WORKER_EXECUTE = "worker.execute"
    VERIFIER_SIGN = "verifier.sign"
    PLAN_BUMP = "plan.bump"
    WORKFLOW_CHECKPOINT = "workflow.checkpoint"
    CUSTOM = "custom"


class TraceSpan(Envelope):
    """A single span inside a trace.

    Spans form a tree via parent_span_id. started_at is set on
    creation; ended_at is set when finish() is called. duration_ms
    is computed automatically when finishing.
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    trace_id: str = Field(..., description="Owning Trace id.")
    span_id: str = Field(..., min_length=1, max_length=64, description="Per-trace unique span key.")
    parent_span_id: str | None = Field(default=None)
    event_type: EventType = Field(default=EventType.CUSTOM)
    name: str = Field(..., min_length=1, max_length=200)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None, ge=0)
    payload: dict = Field(default_factory=dict)
    error: str | None = Field(default=None)
    actor: str = Field(default="kernel", description="Who emitted the span (kernel/worker/verifier/...).")

    @field_validator("started_at")
    @classmethod
    def _started_tz(cls, v):
        if v.tzinfo is None:
            raise ValueError("started_at must be tz-aware")
        return v.astimezone(UTC)

    @field_validator("ended_at")
    @classmethod
    def _ended_tz(cls, v):
        if v is None:
            return None
        if v.tzinfo is None:
            raise ValueError("ended_at must be tz-aware")
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def _no_self_parent(self):
        if self.parent_span_id is not None and self.parent_span_id == self.span_id:
            raise ValueError("TraceSpan cannot be its own parent")
        return self

    def finish(self, error=None):
        """Mark the span finished; compute duration_ms."""
        self.ended_at = utcnow()
        delta = (self.ended_at - self.started_at).total_seconds()
        self.duration_ms = max(0, int(delta * 1000))
        if error is not None:
            self.error = error
        self.touch()

    @property
    def is_finished(self):
        return self.ended_at is not None


class Trace(Envelope):
    """A logical grouping of spans (per-Goal or per-Workflow run)."""

    SCHEMA_VERSION: ClassVar[int] = 1

    goal_id: str | None = Field(default=None, description="Goal this trace belongs to (optional).")
    task_id: str | None = Field(default=None, description="Primary task id, if single-task trace.")
    workflow_run_id: str | None = Field(default=None, description="Workflow run id (T0033).")
    name: str = Field(default="trace", max_length=200)
    spans: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    def add_span(self, span):
        if span.trace_id != self.id:
            span.trace_id = self.id
        if any(s.span_id == span.span_id for s in self.spans):
            raise ValueError(f"span_id {span.span_id!r} already in trace")
        self.spans.append(span)
        self.touch()

    def by_span_id(self, span_id):
        for s in self.spans:
            if s.span_id == span_id:
                return s
        return None

    def root_spans(self):
        return [s for s in self.spans if s.parent_span_id is None]


__all__ = ["Trace", "TraceSpan", "EventType"]
