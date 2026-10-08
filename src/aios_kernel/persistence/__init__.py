"""aios_kernel.persistence - SQLAlchemy ORM + Alembic migrations (T0032).

Submodules:
- models: 8 ORM tables (6 main + 2 auxiliary) + Pydantic<->ORM helpers
- repository: SqlAlchemyRepository (real DB) + create_all/drop_all helpers
- migrations: Alembic env.py + 001_initial.py (T0032 deliverable)
"""
from aios_kernel.persistence.models import (
    ArtifactORM,
    Base,
    EvidenceORM,
    GoalORM,
    PlanORM,
    TaskORM,
    TraceORM,
    VerifierRunORM,
    WorkerRunORM,
    artifact_to_orm,
    envelope_json_of,
    evidence_to_orm,
    goal_to_orm,
    plan_to_orm,
    task_to_orm,
    trace_to_orm,
)
from aios_kernel.persistence.repository import (
    SqlAlchemyRepository,
    create_all,
    drop_all,
)

__all__ = [
    # models
    "Base",
    "GoalORM",
    "TaskORM",
    "PlanORM",
    "ArtifactORM",
    "EvidenceORM",
    "TraceORM",
    "WorkerRunORM",
    "VerifierRunORM",
    "goal_to_orm",
    "task_to_orm",
    "plan_to_orm",
    "artifact_to_orm",
    "evidence_to_orm",
    "trace_to_orm",
    "envelope_json_of",
    # repository
    "SqlAlchemyRepository",
    "create_all",
    "drop_all",
]
