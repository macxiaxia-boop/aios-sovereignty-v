"""repository.py - SQLAlchemy-backed Repository.

Wraps an AsyncSession and exposes the Repository protocol from
aios_kernel.domain.services.repository. The service layer does not
import this module directly; it just calls repo.add(obj) etc.
"""
from __future__ import annotations

from aios_kernel.domain.artifact import Artifact
from aios_kernel.domain.decision import DecisionAudit
from aios_kernel.domain.evidence import Evidence
from aios_kernel.domain.goal import Goal
from aios_kernel.domain.plan import Plan
from aios_kernel.domain.task import Task
from aios_kernel.domain.trace import Trace
from aios_kernel.persistence.models import (
    ArtifactORM,
    Base,
    DecisionAuditORM,
    EvidenceORM,
    GoalORM,
    PlanORM,
    TaskORM,
    TraceORM,
    artifact_to_orm,
    decision_to_orm,
    evidence_to_orm,
    goal_from_orm,
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
    DecisionAudit: (DecisionAuditORM, decision_to_orm),
}


# Mapping from Pydantic class -> from_orm fn (Phase F F001 bidirectional).
# F003 has not yet provided a DecisionAudit.from_orm helper, so we only
# register Goal here. The mapping is intentionally additive (parallel to
# _TO_ORM) so older callers that read raw ORM via repo.get() keep working.
_FROM_ORM = {
    Goal: goal_from_orm,
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

    async def get_domain(self, model, pk):
        """Fetch by pk and rehydrate as the Pydantic domain object.

        Phase F F001: round-trip accessor. Returns the Goal Pydantic
        instance (12 fields) loaded from the ORM row, or None when the
        row does not exist. Only registered Pydantic types in _FROM_ORM
        are supported (currently Goal); other types fall back to the raw
        ORM via ``get()``.
        """
        orm_obj = await self.get(model, pk)
        if orm_obj is None:
            return None
        from_orm = _FROM_ORM.get(model)
        if from_orm is None:
            return orm_obj
        return from_orm(orm_obj)

    async def delete(self, obj):
        if type(obj) not in _TO_ORM:
            raise TypeError(f"unsupported domain type for repository.delete: {type(obj).__name__}")
        orm_cls, to_orm = _TO_ORM[type(obj)]
        orm_obj = to_orm(obj)
        merged = await self.session.merge(orm_obj)
        await self.session.delete(merged)

    async def flush(self):
        await self.session.flush()

    async def find(self, model, **filters):
        """Filter lookup for read-only retrieval.

        Supports the (Pydantic, ORM) pairs registered in _TO_ORM. Each
        keyword argument must match an ORM column; equality is the only
        operator supported (this is intentionally narrow — callers that
        need range / null / order queries can hit the ORM directly).
        Returns a list of ORM instances, empty when nothing matches.

        ``limit`` is honoured when supplied.
        """
        if model not in _TO_ORM:
            raise TypeError(f"unsupported model type for repository.find: {model.__name__}")
        orm_cls, _ = _TO_ORM[model]
        from sqlalchemy import select

        stmt = select(orm_cls)
        for key, value in filters.items():
            if key == "limit":
                continue
            if not hasattr(orm_cls, key):
                raise TypeError(f"unknown filter column on {orm_cls.__name__}: {key!r}")
            stmt = stmt.where(getattr(orm_cls, key) == value)
        limit = filters.get("limit")
        if limit is not None:
            stmt = stmt.limit(int(limit))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


async def create_all(engine):
    """Create all tables (used by tests; migrations go through Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


__all__ = ["SqlAlchemyRepository", "create_all", "drop_all"]