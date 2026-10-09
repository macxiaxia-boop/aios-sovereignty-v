"""models.py - SQLAlchemy ORM (Phase A T0030 §8).

Six main tables (1:1 with Pydantic domain models):
    goals, tasks, plans, artifacts, evidences, traces

Two auxiliary tables (worker / verifier audit):
    worker_runs, verifier_runs

All PKs are String(36) carrying the UUID4 string form.
All time columns are DateTime(timezone=True).
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def envelope_json_of(pyd_obj):
    return json.loads(pyd_obj.model_dump_json())


# 6 main tables
class GoalORM(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    plan_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    # ----- Phase F F001: 10 new GoalContract fields (nullable JSON) -----
    inferred_intent: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    preserve_capabilities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    known_constraints: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    environment_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_modes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    permission_scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approved_tradeoffs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    autonomous_scope: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    requires_authorization: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    tasks = relationship("TaskORM", back_populates="goal", cascade="all, delete-orphan")
    plans = relationship("PlanORM", back_populates="goal", cascade="all, delete-orphan")
    traces = relationship("TraceORM", back_populates="goal", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_goals_status", "status"),
        Index("ix_goals_owner", "owner"),
    )


class TaskORM(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False, default="custom")
    worker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    artifact_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    cost_yuan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    goal = relationship("GoalORM", back_populates="tasks")
    plan = relationship("PlanORM", back_populates="tasks")
    traces = relationship("TraceORM", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tasks_goal_status", "goal_id", "status"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_worker", "worker"),
    )


class PlanORM(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    dependencies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    goal = relationship("GoalORM", back_populates="plans")
    tasks = relationship("TaskORM", back_populates="plan")

    __table_args__ = (
        Index("ix_plans_goal_version", "goal_id", "version"),
        Index("ix_plans_goal_active", "goal_id", "is_active"),
    )


class ArtifactORM(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False, default="file")
    path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    inline_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    inline_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_artifacts_task", "task_id"),
        Index("ix_artifacts_hash", "hash_sha256"),
    )


class EvidenceORM(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    artifact_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    verifier_id: Mapped[str] = mapped_column(String(100), nullable=False)
    verdict: Mapped[str] = mapped_column(String(10), nullable=False, default="BLOCKED")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recheck_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cost_yuan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_evidences_task", "task_id"),
        Index("ix_evidences_verifier_verdict", "verifier_id", "verdict"),
    )


class TraceORM(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="CASCADE"), nullable=True
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    workflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="trace")
    spans: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    goal = relationship("GoalORM", back_populates="traces")
    task = relationship("TaskORM", back_populates="traces")

    __table_args__ = (
        Index("ix_traces_goal", "goal_id"),
        Index("ix_traces_task", "task_id"),
        Index("ix_traces_workflow", "workflow_run_id"),
    )


class WorkerRunORM(Base):
    """Audit row per worker execute() call (T0034)."""
    __tablename__ = "worker_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    worker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cost_yuan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_worker_runs_task", "task_id"),
        Index("ix_worker_runs_status", "status"),
    )


class VerifierRunORM(Base):
    """Audit row per verifier sign() call (T0035)."""
    __tablename__ = "verifier_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    verifier_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verdict: Mapped[str] = mapped_column(String(10), nullable=False, default="BLOCKED")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_yuan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_verifier_runs_task", "task_id"),
        Index("ix_verifier_runs_verdict", "verdict"),
    )


# Pydantic -> ORM helpers
def goal_to_orm(p):
    """Convert Goal (Pydantic 12-field GoalContract) -> GoalORM.

    The 10 new Phase F F001 fields are mapped 1:1 to JSON columns. Each
    sub-model (Constraint, EnvSnapshot, FailureMode, PermissionScope,
    EvidenceRequest, Tradeoff, OpType) is dumped to dict via
    ``model_dump(mode='json')`` so the resulting JSON is JSON-portable
    (datetimes -> ISO strings). The companion ``goal_from_orm`` reconstructs
    the Pydantic models from the same JSON.
    """
    import json as _json
    from aios_kernel.domain.goal import (
        Constraint,
        EnvSnapshot,
        EvidenceRequest,
        FailureMode,
        OpType,
        PermissionScope,
        Tradeoff,
    )

    def _dump(items, model_cls):
        # Each item is already a model instance; round-trip via model_dump
        # so we get JSON-friendly dicts (datetime -> ISO, Enum -> value).
        return [_json.loads(item.model_dump_json()) if isinstance(item, model_cls)
                else dict(item) for item in (items or [])]

    def _dump_one(obj, model_cls):
        if obj is None:
            return None
        if isinstance(obj, model_cls):
            return _json.loads(obj.model_dump_json())
        return dict(obj)

    return GoalORM(
        id=p.id,
        title=p.title,
        description=p.description,
        success_criteria=p.success_criteria,
        budget=p.budget,
        deadline=p.deadline,
        owner=p.owner,
        status=p.status.value if hasattr(p.status, "value") else str(p.status),
        tags=list(p.tags),
        plan_ids=list(p.plan_ids),
        metadata_=dict(p.metadata),
        # Phase F F001: 10 new fields (JSON dump)
        inferred_intent=p.inferred_intent,
        preserve_capabilities=list(p.preserve_capabilities or []),
        known_constraints=_dump(p.known_constraints, Constraint),
        environment_context=_dump_one(p.environment_context, EnvSnapshot),
        failure_modes=_dump(p.failure_modes, FailureMode),
        permission_scope=_dump_one(p.permission_scope, PermissionScope),
        missing_evidence=_dump(p.missing_evidence, EvidenceRequest),
        approved_tradeoffs=_dump(p.approved_tradeoffs, Tradeoff),
        autonomous_scope=_dump(p.autonomous_scope, OpType),
        requires_authorization=_dump(p.requires_authorization, OpType),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def goal_from_orm(o):
    """Convert GoalORM -> Goal (12-field GoalContract).

    Companion to ``goal_to_orm``. Re-hydrates the 7 sub-models from their
    JSON columns. Missing/None entries are coerced to the default empty
    value so an old (Phase A) row that never had the new columns can still
    be loaded.
    """
    from aios_kernel.domain.goal import (
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

    def _load_list(items, model_cls):
        if not items:
            return []
        return [model_cls.model_validate(item) for item in items]

    def _load_one(obj, model_cls):
        if obj is None:
            return None
        return model_cls.model_validate(obj)

    status_value = o.status if hasattr(o.status, "__str__") else str(o.status)
    try:
        status = GoalStatus(status_value)
    except ValueError:
        status = GoalStatus.PENDING

    return Goal(
        id=o.id,
        title=o.title,
        description=o.description,
        success_criteria=o.success_criteria,
        budget=o.budget,
        deadline=o.deadline,
        owner=o.owner,
        status=status,
        tags=list(o.tags or []),
        plan_ids=list(o.plan_ids or []),
        metadata=dict(o.metadata_ or {}),
        # Phase F F001: 10 new fields (JSON load)
        inferred_intent=getattr(o, "inferred_intent", None),
        preserve_capabilities=list(getattr(o, "preserve_capabilities", []) or []),
        known_constraints=_load_list(getattr(o, "known_constraints", []) or [], Constraint),
        environment_context=_load_one(getattr(o, "environment_context", None), EnvSnapshot),
        failure_modes=_load_list(getattr(o, "failure_modes", []) or [], FailureMode),
        permission_scope=_load_one(getattr(o, "permission_scope", None), PermissionScope),
        missing_evidence=_load_list(getattr(o, "missing_evidence", []) or [], EvidenceRequest),
        approved_tradeoffs=_load_list(getattr(o, "approved_tradeoffs", []) or [], Tradeoff),
        autonomous_scope=_load_list(getattr(o, "autonomous_scope", []) or [], OpType),
        requires_authorization=_load_list(getattr(o, "requires_authorization", []) or [], OpType),
        schema_version=getattr(o, "schema_version", 2),
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def task_to_orm(p):
    return TaskORM(
        id=p.id,
        goal_id=p.goal_id,
        title=p.title,
        description=p.description,
        task_type=p.task_type.value if hasattr(p.task_type, "value") else str(p.task_type),
        worker=p.worker,
        plan_id=p.plan_id,
        plan_version=p.plan_version,
        status=p.status.value if hasattr(p.status, "value") else str(p.status),
        evidence_ids=list(p.evidence_ids),
        artifact_ids=list(p.artifact_ids),
        retry_count=p.retry_count,
        max_retries=p.max_retries,
        cost_yuan=p.cost_yuan,
        started_at=p.started_at,
        completed_at=p.completed_at,
        error=p.error,
        input_payload=dict(p.input_payload),
        output_payload=dict(p.output_payload),
        metadata_=dict(p.metadata),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def plan_to_orm(p):
    return PlanORM(
        id=p.id,
        goal_id=p.goal_id,
        version=p.version,
        is_active=p.is_active,
        parent_version=p.parent_version,
        title=p.title,
        description=p.description,
        rollback_to=p.rollback_to,
        created_by=p.created_by,
        steps=[s.model_dump() for s in p.steps],
        dependencies=[d.model_dump() for d in p.dependencies],
        metadata_=dict(p.metadata),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def artifact_to_orm(p):
    return ArtifactORM(
        id=p.id,
        task_id=p.task_id,
        artifact_type=p.artifact_type.value if hasattr(p.artifact_type, "value") else str(p.artifact_type),
        path=p.path,
        inline_content=p.inline_content,
        inline_json=p.inline_json,
        hash_sha256=p.hash_sha256,
        size_bytes=p.size_bytes,
        mime_type=p.mime_type,
        label=p.label,
        metadata_=dict(p.metadata),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def evidence_to_orm(p):
    return EvidenceORM(
        id=p.id,
        task_id=p.task_id,
        artifact_ids=list(p.artifact_ids),
        verifier_id=p.verifier_id,
        verdict=p.verdict.value if hasattr(p.verdict, "value") else str(p.verdict),
        details=dict(p.details),
        signed_at=p.signed_at,
        recheck_required=p.recheck_required,
        cost_yuan=p.cost_yuan,
        error=p.error,
        evidence_hash=p.evidence_hash,
        metadata_=dict(p.metadata),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def trace_to_orm(p):
    return TraceORM(
        id=p.id,
        goal_id=p.goal_id,
        task_id=p.task_id,
        workflow_run_id=p.workflow_run_id,
        name=p.name,
        spans=[s.model_dump() for s in p.spans],
        metadata_=dict(p.metadata),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


__all__ = [
    "Base",
    "GoalORM",
    "TaskORM",
    "PlanORM",
    "ArtifactORM",
    "EvidenceORM",
    "TraceORM",
    "WorkerRunORM",
    "VerifierRunORM",
    "LongTermMemoryORM",
    "DecisionAuditORM",
    "goal_to_orm",
    "goal_from_orm",
    "task_to_orm",
    "plan_to_orm",
    "artifact_to_orm",
    "evidence_to_orm",
    "trace_to_orm",
    "long_term_memory_to_orm",
    "decision_to_orm",
    "envelope_json_of",
]


# ---------------------------------------------------------------------------
# Phase B B003 - Long-term Memory (cross-session persistent knowledge).
# ---------------------------------------------------------------------------
class LongTermMemoryORM(Base):
    __tablename__ = "long_term_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_ltm_key", "key"),
        Index("ix_ltm_created_at", "created_at"),
        Index("ix_ltm_source_evidence_id", "source_evidence_id"),
    )


def long_term_memory_to_orm(p):
    """Convert LongTermEntry (Pydantic) -> LongTermMemoryORM."""
    from aios_kernel.context.long_term_memory import LongTermEntry
    assert isinstance(p, LongTermEntry), f"expected LongTermEntry, got {type(p).__name__}"
    return LongTermMemoryORM(
        id=p.id,
        key=p.key,
        value_json=dict(p.value) if isinstance(p.value, dict) else {"data": p.value},
        created_at=p.created_at,
        updated_at=p.updated_at,
        expires_at=p.expires_at,
        retention_days=p.retention_days,
        tags=list(p.tags),
        source_evidence_id=str(p.source_evidence_id) if p.source_evidence_id else None,
        schema_version=p.schema_version,
    )


# ---------------------------------------------------------------------------
# Phase B B002 - Working Memory (short-lived per-session state).
# ---------------------------------------------------------------------------
class WorkingMemoryORM(Base):
    __tablename__ = "working_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_wm_session_key", "session_id", "key", unique=True),
        Index("ix_wm_expires", "expires_at"),
    )


def working_memory_to_orm(p):
    from aios_kernel.context.working_memory import WorkingMemoryEntry
    if not isinstance(p, WorkingMemoryEntry):
        raise TypeError(f"expected WorkingMemoryEntry, got {type(p).__name__}")
    return WorkingMemoryORM(
        id=str(p.id),
        session_id=p.session_id,
        key=p.key,
        value_json=dict(p.value),
        created_at=p.created_at,
        updated_at=p.updated_at,
        expires_at=p.expires_at,
        schema_version=p.schema_version,
    )


def working_memory_from_orm(o):
    from aios_kernel.context.working_memory import WorkingMemoryEntry
    return WorkingMemoryEntry(
        id=o.id,
        session_id=o.session_id,
        key=o.key,
        value=dict(o.value_json or {}),
        created_at=o.created_at,
        updated_at=o.updated_at,
        expires_at=o.expires_at,
        schema_version=o.schema_version,
    )
# ---------------------------------------------------------------------------
# Phase B B005 - Knowledge RAG (documents + chunks + embeddings).
# ---------------------------------------------------------------------------
class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    chunks = relationship(
        "DocumentChunkORM", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_title", "title"),
        Index("ix_documents_created_at", "created_at"),
    )


class DocumentChunkORM(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_token: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_token: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document = relationship("DocumentORM", back_populates="chunks")
    embedding = relationship(
        "EmbeddingORM",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_chunks_doc_id_index", "doc_id", "chunk_index", unique=True),
        Index("ix_chunks_doc_id", "doc_id"),
    )


class EmbeddingORM(Base):
    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="hash-dev-1536")
    dim: Mapped[int] = mapped_column(Integer, nullable=False, default=1536)
    # SQLite + numpy cosine in dev. In production this becomes pgvector.
    vector_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    norm: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    chunk = relationship("DocumentChunkORM", back_populates="embedding")

    __table_args__ = (
        Index("ix_embeddings_chunk_id", "chunk_id"),
        Index("ix_embeddings_model", "model"),
    )
# ---------------------------------------------------------------------------
# Phase F F003 - Decision Audit Log (every AIOS decision gets one row).
# ---------------------------------------------------------------------------
class DecisionAuditORM(Base):
    """DecisionAudit persistence layer.

    One row per auditable decision (route dispatch / GoalContract parse /
    failure merge / intent interpretation / operator override). Indexes on
    goal_id (per-goal chain lookup), actor (per-actor history), and outcome
    (pending-list sweep).

    FK goal_id -> goals.id ON DELETE CASCADE: when a Goal is purged, its
    audit chain disappears with it. Schema mirrors the Pydantic
    DecisionAudit exactly (see aios_kernel.domain.decision).
    """

    __tablename__ = "decision_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    alternatives: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    chosen: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    outcome_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    envelope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_decision_audit_goal_id", "goal_id"),
        Index("ix_decision_audit_actor", "actor"),
        Index("ix_decision_audit_outcome", "outcome"),
    )


def decision_to_orm(p):
    """Convert DecisionAudit (Pydantic) -> DecisionAuditORM.

    Mirrors the existing to_orm pattern (Goal/Task/...). Enums are flattened
    to their string values so SQLite/JSONB lookups stay portable.
    """
    from aios_kernel.domain.decision import DecisionAudit

    if not isinstance(p, DecisionAudit):
        raise TypeError(f"expected DecisionAudit, got {type(p).__name__}")
    return DecisionAuditORM(
        id=p.id,
        goal_id=p.goal_id,
        actor=p.actor.value if hasattr(p.actor, "value") else str(p.actor),
        rationale=p.rationale,
        alternatives=list(p.alternatives),
        chosen=p.chosen,
        outcome=p.outcome.value if hasattr(p.outcome, "value") else str(p.outcome),
        outcome_detail=p.outcome_detail,
        confidence=float(p.confidence),
        tags=list(p.tags),
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
