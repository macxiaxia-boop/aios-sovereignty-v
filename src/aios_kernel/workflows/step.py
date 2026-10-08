"""step.py - WorkflowStep, StepMeta, StepStatus, RetryPolicy.

T0033 — Durable Execution Adapter. Atomic step type for WorkflowEngine.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

# ---------- Status ----------------------------------------------------------


class StepStatus(str, Enum):
    """Per-step lifecycle status.

    Pending   - not started yet (workflow just enqueued this step)
    Running   - activity.execute() in flight
    Completed - execute() returned success
    Failed    - execute() raised or returned error after exhausting retries
    Skipped   - upstream step failed, so this step was skipped
    Compensated - execute() failed AND compensate() succeeded (Saga pattern)
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATED = "compensated"


# ---------- Retry policy ----------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff retry.

    delay(attempt) = min(initial_delay_s * backoff_factor ** (attempt - 1), max_delay_s)
    attempt is 1-based; the first attempt is attempt=1, retry kicks in for attempt>=2.
    """

    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay_s: float = 0.01
    max_delay_s: float = 1.0

    def delay_for(self, attempt: int) -> float:
        """Return the sleep duration before attempt N (1-based).

        attempt=1 -> 0 (no sleep before first try)
        attempt=2 -> initial_delay_s
        attempt=3 -> initial_delay_s * backoff_factor
        attempt=N -> min(initial_delay_s * backoff_factor ** (N-1), max_delay_s)
        """
        if attempt <= 1:
            return 0.0
        raw = self.initial_delay_s * (self.backoff_factor ** (attempt - 2))
        return min(raw, self.max_delay_s)


# ---------- Activity protocol ----------------------------------------------


@runtime_checkable
class Activity(Protocol):
    """Atomic unit of work. Implementations MUST be idempotent.

    engine calls execute() with the same ctx payload after a restart — the
    activity must be safe to re-run. Side effects should be checked against
    state in ctx before doing the actual work.
    """

    name: str

    async def execute(self, ctx: ActivityContext) -> ActivityResult: ...

    async def compensate(self, ctx: ActivityContext) -> None:
        """Optional compensation. Default: no-op (covered by AC failure path)."""
        return None


# Activity factory shorthand: any async-callable that takes ctx can be wrapped
ActivityFactory = Callable[["ActivityContext"], Awaitable["ActivityResult"]]


def from_callable(
    name: str,
    fn: ActivityFactory,
    compensate_fn: ActivityFactory | None = None,
) -> CallableActivity:
    """Lift a plain async function into an Activity. Useful for tests/examples."""
    return CallableActivity(name=name, fn=fn, compensate_fn=compensate_fn)


@dataclass
class CallableActivity:
    """Adapter so any async callable satisfies the Activity protocol."""

    name: str
    fn: ActivityFactory
    compensate_fn: ActivityFactory | None = None

    async def execute(self, ctx: ActivityContext) -> ActivityResult:
        return await self.fn(ctx)

    async def compensate(self, ctx: ActivityContext) -> None:
        if self.compensate_fn is not None:
            await self.compensate_fn(ctx)


# ---------- ActivityContext / ActivityResult -------------------------------


@dataclass
class ActivityContext:
    """Bag of state passed to Activity.execute / Activity.compensate.

    State persists across retries inside the same step run.
    """

    run_id: str
    step_id: str
    attempt: int
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "attempt": self.attempt,
            "input": self.input,
            "output": self.output,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivityContext:
        return cls(
            run_id=str(data.get("run_id", "")),
            step_id=str(data.get("step_id", "")),
            attempt=int(data.get("attempt", 1)),
            input=dict(data.get("input", {})),
            output=dict(data.get("output", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ActivityResult:
    """Result of a single execute() call (NOT the whole step).

    success=False  -> engine triggers retry per RetryPolicy.
    error is set when success=False.
    """

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"success": self.success, "output": self.output, "error": self.error}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivityResult:
        return cls(
            success=bool(data.get("success", False)),
            output=dict(data.get("output", {})),
            error=data.get("error"),
        )


# ---------- Step ------------------------------------------------------------


@dataclass(frozen=True)
class StepMeta:
    """Step metadata. id and name; activity binding is in WorkflowStep.

    id is used as the FK in workflow_checkpoints; must be unique within
    the workflow.
    """

    id: str
    name: str
    description: str = ""


@dataclass
class WorkflowStep:
    """One step in a workflow DAG.

    depends_on: list of step ids that must complete before this step runs.
    retry_policy: None -> default RetryPolicy() (3 attempts, exp backoff).
    timeout_s: per-attempt timeout via asyncio.wait_for; None = no timeout.
    """

    meta: StepMeta
    activity: Activity
    depends_on: list[str] = field(default_factory=list)
    retry_policy: RetryPolicy | None = None
    timeout_s: float | None = None

    def __post_init__(self) -> None:
        if not self.meta.id:
            raise ValueError("StepMeta.id must be non-empty")
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()

    @property
    def id(self) -> str:
        return self.meta.id

    @property
    def name(self) -> str:
        return self.meta.name

    def effective_retry_policy(self) -> RetryPolicy:
        return self.retry_policy or RetryPolicy()
