"""aios_kernel.domain \u2014 Pydantic models for Goal / Task / Plan / State.

This package contains only Pydantic v2 schemas (no SQLAlchemy, no IO). The
persistence layer in ``aios_kernel.persistence`` maps these models to ORM
rows; the services layer in ``aios_kernel.domain.services`` orchestrates
the two together.
"""
from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.domain.decision import DecisionActor, DecisionAudit, DecisionOutcome
from aios_kernel.domain.envelope import Envelope, utcnow
from aios_kernel.domain.evidence import Evidence, Verdict
from aios_kernel.domain.goal import (
    ALLOWED_OPS,
    GOAL_TRANSITIONS,
    Constraint,
    EnvSnapshot,
    EvidenceRequest,
    FailureMode,
    Goal,
    GoalStatus,
    OpType,
    PermissionScope,
    Tradeoff,
)
from aios_kernel.domain.plan import (
    Dependency,
    DependencyKind,
    Plan,
    PlanStep,
    StepType,
)
from aios_kernel.domain.task import TASK_TRANSITIONS, Task, TaskStatus, TaskType
from aios_kernel.domain.trace import EventType, Trace, TraceSpan

__all__ = [
    # base
    "Envelope",
    "utcnow",
    # goal
    "Goal",
    "GoalStatus",
    "GOAL_TRANSITIONS",
    # Phase F F001 sub-models
    "Constraint",
    "EnvSnapshot",
    "FailureMode",
    "PermissionScope",
    "EvidenceRequest",
    "Tradeoff",
    "OpType",
    "ALLOWED_OPS",
    # task
    "Task",
    "TaskStatus",
    "TaskType",
    "TASK_TRANSITIONS",
    # plan
    "Plan",
    "PlanStep",
    "Dependency",
    "StepType",
    "DependencyKind",
    # artifact
    "Artifact",
    "ArtifactType",
    # evidence
    "Evidence",
    "Verdict",
    # trace
    "Trace",
    "TraceSpan",
    "EventType",
    # decision audit (Phase F F003)
    "DecisionActor",
    "DecisionAudit",
    "DecisionOutcome",
]