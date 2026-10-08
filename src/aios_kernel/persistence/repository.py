"""repository.py - SQLAlchemy-backed Repository.

Wraps an AsyncSession and exposes the Repository protocol from
aios_kernel.domain.services.repository. The service layer does not
import this module directly; it just calls repo.add(obj) etc.
"""
from __future__ import annotations

from aios_kernel.domain.artifact import Artifact
from aios_kernel.domain.evidence import Evidence
from aios_kernel.domain.goal import Goal
from aios_kernel.domain.plan import Plan
from aios_kernel.domain.task import Task
from aios_kernel.domain.trace import Trace
from aios_kernel.persistence.models import (
    ArtifactORM,
    Base,
    EvidenceORM,
    GoalORM,
    PlanORM,
    TaskORM,
    TraceORM,
    artifact_to_orm,
    evidence_to_orm,
    goal_to_orm,
    plan_to_orm,
    task_to_orm,
    trace_to_orm,
)

# Mapping from Pydantic class -> (ORM class, to_orm fn)
_TO_ORM = {
    Goal: (GoalORM, goal_to_orm),
    Task: (TaskORM, task_to_orm),
    Plan: (PlanORM, plan_to_orm),
    Artifact: (ArtifactORM, artifact_to_orm),
    Evidence: (EvidenceORM, evidence_to_orm),
    Trace: (TraceORM, trace_to_orm),
}


class SqlAlchemyRepository:
    """Async SQLAlchemy-backed Repository.

    Usage:
        engine = make_engine("sqlite+aiosqlite:///aios_kernel.db")
        factory = make_session_factory(engine)
        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            await repo.add(goal)
    """

    def __init__(self, session):
        self.session = session

    async def add(self, obj):
        if type(obj) not in _TO_ORM:
            raise TypeError(f"unsupported domain type for repository.add: {type(obj).__name__}")
        orm_cls, to_orm = _TO_ORM[type(obj)]
        orm_obj = to_orm(obj)
        await self.session.merge(orm_obj)

    async def commit(self):
        await self.session.commit()

    async def refresh(self, obj):
        await self.session.refresh(obj)

    async def get(self, model, pk):
        if model not in _TO_ORM:
            raise TypeError(f"unsupported model type for repository.get: {model.__name__}")
        orm_cls, _ = _TO_ORM[model]
        result = await self.session.get(orm_cls, pk)
        return result

    async def delete(self, obj):
        if type(obj) not in _TO_ORM:
            raise TypeError(f"unsupported domain type for repository.delete: {type(obj).__name__}")
        orm_cls, to_orm = _TO_ORM[type(obj)]
        orm_obj = to_orm(obj)
        merged = await self.session.merge(orm_obj)
        await self.session.delete(merged)

    async def flush(self):
        await self.session.flush()


async def create_all(engine):
    """Create all tables (used by tests; migrations go through Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


__all__ = ["SqlAlchemyRepository", "create_all", "drop_all"]
