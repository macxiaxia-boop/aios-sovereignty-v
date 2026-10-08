"""plan.py — Plan + PlanStep + Dependency (Phase A T0030 §4 + §2 判据 3).

A Plan is a versioned, ordered set of steps that execute against a Goal.
Version auto-increments on every create_version() call (T0032 §Services).
Each step is a typed reference to a Task (the actual Task rows are owned by
the TaskService; Plan only references them by id).

The 5-version acceptance test (T0030 §2 判据 3) is covered by
tests/unit/test_plan_versioning.py.
"""
from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import Field, model_validator

from aios_kernel.domain.envelope import Envelope


class StepType(str, Enum):
    """Type of work a PlanStep represents.

    Mirrors the T0030 §2 判据 1..9 plan vocabulary; custom is the catch-all.
    """

    TASK = "task"
    REVIEW = "review"
    APPROVAL = "approval"
    CUSTOM = "custom"


class DependencyKind(str, Enum):
    """How a PlanStep depends on another."""

    FINISH_TO_START = "FS"   # upstream Done -> downstream may start
    START_TO_START = "SS"    # upstream Started -> downstream may start
    MANUAL = "MANUAL"        # human/manual gate


class PlanStep(Envelope):
    """A single step inside a Plan.

    Carries the structural shape (kind, depends_on, assignee_hint). The
    runtime task instance is referenced by task_id (set when the step
    is dispatched to a worker in T0033/T0034).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    plan_id: str = Field(..., description="Owning Plan id.")
    name: str = Field(..., min_length=1, max_length=200)
    kind: StepType = Field(default=StepType.TASK)
    assignee_hint: str | None = Field(
        default=None, description="Preferred worker adapter name (T0034 maps to real)."
    )
    depends_on: list = Field(
        default_factory=list, description="Other step ids this step waits on."
    )
    dependency_kind: DependencyKind = Field(default=DependencyKind.FINISH_TO_START)
    task_id: str | None = Field(default=None, description="Task id once dispatched.")
    order: int = Field(default=0, ge=0, description="Stable ordering within the plan.")
    timeout_seconds: int | None = Field(default=None, ge=1)
    input_payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _no_self_dep(self):
        if self.id in self.depends_on:
            raise ValueError("PlanStep cannot depend on itself")
        return self


class Dependency(Envelope):
    """Standalone edge between two PlanSteps (alternative to PlanStep.depends_on).

    Used when a plan author needs the dependency graph to be queryable as
    its own entity (for cycle detection, visualization, etc.).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    plan_id: str = Field(...)
    from_step_id: str = Field(...)
    to_step_id: str = Field(...)
    kind: DependencyKind = Field(default=DependencyKind.FINISH_TO_START)

    @model_validator(mode="after")
    def _no_self_edge(self):
        if self.from_step_id == self.to_step_id:
            raise ValueError("Dependency cannot have from_step_id == to_step_id")
        return self


class Plan(Envelope):
    """A versioned plan for a Goal.

    version is a monotonically increasing int (per goal) — PlanService
    auto-increments it on every create_version() call. Plans with
    is_active=False are historical revisions kept for audit / rollback.
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    goal_id: str = Field(...)
    version: int = Field(default=1, ge=1, description="Monotonic per-goal version.")
    is_active: bool = Field(default=True, description="Whether this plan is the live one.")
    parent_version: int | None = Field(
        default=None, ge=1, description="Previous plan version this one forked from."
    )
    steps: list = Field(default_factory=list)
    dependencies: list = Field(default_factory=list)
    title: str = Field(default="", max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    rollback_to: int | None = Field(default=None, ge=1, description="Target version on rollback.")
    created_by: str = Field(default="system", description="Agent/user who created the plan.")
    metadata: dict = Field(default_factory=dict)

    # ---------- helpers -----------------------------------------------------

    def step_ids(self):
        return [s.id for s in self.steps]

    def by_id(self, step_id):
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def add_step(self, step):
        if step.plan_id != self.id:
            step.plan_id = self.id
        if step.id in self.step_ids():
            raise ValueError(f"step {step.id!r} already in plan")
        self.steps.append(step)
        self.touch()

    def add_dependency(self, dep):
        if dep.plan_id != self.id:
            dep.plan_id = self.id
        if dep.from_step_id not in self.step_ids() or dep.to_step_id not in self.step_ids():
            raise ValueError("dependency references unknown step")
        self.dependencies.append(dep)
        self.touch()

    def bump_version(self):
        """Increment version in place; return the new value."""
        self.version = self.version + 1
        self.is_active = True
        self.touch()
        return self.version

    def mark_inactive(self):
        self.is_active = False
        self.touch()


__all__ = ["Plan", "PlanStep", "Dependency", "StepType", "DependencyKind"]
