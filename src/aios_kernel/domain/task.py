"""task.py — Task aggregate (Phase A T0030 §4 + §2 判据 2).

A Task is one unit of work inside a Goal. Tasks are dispatched to a Worker
via a T0034 adapter. State transitions are governed by the 8-state machine
specified in the T0030 acceptance criteria.

Status machine (8 states):
    Pending -> Running -> Verifying -> Done
    Pending -> Running -> Verifying -> Failed
    Pending -> Running -> Blocked
    Running -> Failed  (worker fatal error)
    Blocked -> Running (manual unblock)
    Verifying -> Running (verifier requested redo)
    Done / Failed are terminal
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope, utcnow


class TaskStatus(str, Enum):
    """8 lifecycle states for a Task (T0030 §2 判据 2)."""

    PENDING = "Pending"
    RUNNING = "Running"
    VERIFYING = "Verifying"
    DONE = "Done"
    FAILED = "Failed"
    BLOCKED = "Blocked"

    @classmethod
    def terminal(cls):
        return {cls.DONE, cls.FAILED}


class TaskType(str, Enum):
    """The 5 T0040 mock task types, kept here so worker dispatch can route."""

    FILE_SUMMARY = "file_summary"
    STRING_FORMAT = "string_format"
    MATH_CALC = "math_calc"
    ENV_PROBE = "env_probe"
    CROSS_WORKER = "cross_worker"
    # Custom user-defined tasks fall into this bucket:
    CUSTOM = "custom"


# Allowed forward transitions (T0030 §2 判据 2: 8 states, 8 valid transitions).
TASK_TRANSITIONS: dict = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {
        TaskStatus.VERIFYING,
        TaskStatus.FAILED,
        TaskStatus.BLOCKED,
    },
    TaskStatus.VERIFYING: {TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.RUNNING},
    TaskStatus.BLOCKED: {TaskStatus.RUNNING, TaskStatus.FAILED},
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
}


class Task(Envelope):
    """One unit of work inside a Goal.

    Carries the worker binding (worker), plan binding (plan_version)
    and a list of evidence ids the worker produced (T0035 Verifier signs
    them, then the Task transitions to Done).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    goal_id: str = Field(..., description="Parent Goal id.")
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    task_type: TaskType = Field(default=TaskType.CUSTOM)
    worker: str | None = Field(
        default=None,
        description="Bound worker adapter name (e.g. 'CodexAdapter'); set by dispatcher.",
    )
    plan_id: str | None = Field(default=None, description="Owning Plan id.")
    plan_version: int = Field(default=1, ge=1, description="Plan version when this task was issued.")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    evidence_ids: list = Field(default_factory=list, description="Evidence ids produced.")
    artifact_ids: list = Field(default_factory=list, description="Artifact ids produced.")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts so far.")
    max_retries: int = Field(default=3, ge=0)
    cost_yuan: float = Field(default=0.0, ge=0.0, description="Accumulated cost in CNY (¥).")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    error: str | None = Field(default=None, description="Last error message, if any.")
    input_payload: dict = Field(default_factory=dict)
    output_payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    @field_validator("started_at", "completed_at")
    @classmethod
    def _tz(cls, value):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime must be tz-aware")
        return value.astimezone(UTC)

    # ---------- state machine helpers --------------------------------------

    def can_transition_to(self, new_status):
        return new_status in TASK_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"illegal Task status transition: {self.status.value} -> {new_status.value}"
            )
        now = utcnow()
        if new_status == TaskStatus.RUNNING and self.started_at is None:
            self.started_at = now
        if new_status in TaskStatus.terminal():
            self.completed_at = now
        self.status = new_status
        self.touch()
        return self

    @property
    def is_terminal(self):
        return self.status in TaskStatus.terminal()

    def add_evidence(self, evidence_id):
        if evidence_id and evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.touch()

    def add_artifact(self, artifact_id):
        if artifact_id and artifact_id not in self.artifact_ids:
            self.artifact_ids.append(artifact_id)
            self.touch()


__all__ = ["Task", "TaskStatus", "TaskType", "TASK_TRANSITIONS"]
