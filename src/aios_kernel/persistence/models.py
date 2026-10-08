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
        envelope_json=envelope_json_of(p),
        schema_version=p.schema_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
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
    "goal_to_orm",
    "task_to_orm",
    "plan_to_orm",
    "artifact_to_orm",
    "evidence_to_orm",
    "trace_to_orm",
    "long_term_memory_to_orm",
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
