"""workflow.py - Workflow (DAG of steps) + validation.

T0033 — Durable Execution Adapter. Top-level container for WorkflowStep
nodes with dependency edges.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .step import StepStatus, WorkflowStep

# ---------- Workflow-level status ------------------------------------------


class WorkflowStatus(str, Enum):
    """Top-level workflow run status.

    PENDING    - run created but not started
    RUNNING    - at least one step has started
    COMPLETED  - all steps completed successfully
    FAILED     - at least one step permanently failed
    CANCELLED  - cancel() was called and honored
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------- Signal / Query / Run value objects -----------------------------


@dataclass(frozen=True)
class Signal:
    """External signal delivered to a run via engine.signal().

    Phase A: only "cancel" is honored natively; other signal types are
    stored in the run metadata for future extension.
    """

    type: str  # "cancel" | "custom:<name>"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Query:
    """Read-only query against a run. Phase A: "status" | "step:<id>"."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRun:
    """In-memory representation of a workflow_runs row + per-step state cache."""

    run_id: str
    workflow_id: str
    status: WorkflowStatus
    current_step: str | None
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    step_states: dict[str, StepStatus] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "step_states": {k: v.value for k, v in self.step_states.items()},
            "metadata": self.metadata,
        }


# ---------- Workflow definition --------------------------------------------


@dataclass
class Workflow:
    """A DAG of WorkflowStep nodes.

    steps: unordered set of nodes; dependencies in each step.depends_on
    form the edges. The engine topologically sorts at run time.

    validation in __post_init__:
      - duplicate step ids -> ValueError
      - depends_on references a missing step -> ValueError
      - cycle in the DAG -> ValueError
    """

    id: str
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Workflow.id must be non-empty")
        if not self.steps:
            raise ValueError("Workflow must have at least one step")
        self._validate()

    def _validate(self) -> None:
        ids: set[str] = set()
        for s in self.steps:
            if s.id in ids:
                raise ValueError(f"duplicate step id: {s.id!r}")
            ids.add(s.id)
        for s in self.steps:
            for dep in s.depends_on:
                if dep not in ids:
                    raise ValueError(
                        f"step {s.id!r} depends on unknown step {dep!r}"
                    )
        self._check_cycles(ids)

    def _check_cycles(self, ids: set[str]) -> None:
        # Kahn's algorithm
        in_degree: dict[str, int] = {sid: 0 for sid in ids}
        adjacency: dict[str, list[str]] = {sid: [] for sid in ids}
        for s in self.steps:
            for dep in s.depends_on:
                adjacency[dep].append(s.id)
                in_degree[s.id] += 1
        ready = sorted([sid for sid, d in in_degree.items() if d == 0])
        visited = 0
        while ready:
            nxt = ready.pop(0)
            visited += 1
            for child in adjacency[nxt]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    ready.append(child)
        if visited != len(ids):
            cycle_members = [sid for sid, d in in_degree.items() if d > 0]
            raise ValueError(
                f"cycle detected in workflow {self.id!r}; unresolved={cycle_members}"
            )

    def step_by_id(self, step_id: str) -> WorkflowStep:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(f"no step {step_id!r} in workflow {self.id!r}")

    def topological_order(self) -> list[WorkflowStep]:
        """Return steps in valid execution order (parents before children)."""
        in_degree: dict[str, int] = {s.id: 0 for s in self.steps}
        adjacency: dict[str, list[str]] = {s.id: [] for s in self.steps}
        for s in self.steps:
            for dep in s.depends_on:
                adjacency[dep].append(s.id)
                in_degree[s.id] += 1
        ready = sorted([s.id for s in self.steps if in_degree[s.id] == 0])
        order: list[WorkflowStep] = []
        by_id = {s.id: s for s in self.steps}
        while ready:
            nxt = ready.pop(0)
            order.append(by_id[nxt])
            for child in adjacency[nxt]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    ready.append(child)
        if len(order) != len(self.steps):
            raise ValueError("cycle detected during topo sort")
        return order

    def next_step_after(self, last_step_id: str | None) -> WorkflowStep | None:
        """Return the next step in topological order after `last_step_id`.

        Used by restart recovery. If `last_step_id` is None, returns the
        first ready step. If the workflow is finished, returns None.
        """
        order = self.topological_order()
        if last_step_id is None:
            return order[0] if order else None
        for i, s in enumerate(order):
            if s.id == last_step_id:
                if i + 1 < len(order):
                    return order[i + 1]
                return None
        raise KeyError(f"step {last_step_id!r} not in workflow {self.id!r}")

    def iter_steps(self) -> Iterator[WorkflowStep]:
        return iter(self.steps)


def new_run_id() -> str:
    """Generate a run id (uuid4 hex)."""
    return uuid.uuid4().hex
