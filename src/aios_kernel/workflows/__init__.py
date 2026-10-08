"""workflows - durable execution for AIOS Kernel (T0033).

Exports:
  - WorkflowEngine: Protocol
  - PGCheckpointerEngine: SQLAlchemy-async, 3-table checkpointing
  - Workflow / WorkflowRun / WorkflowStatus / Signal / Query
  - WorkflowStep / StepMeta / StepStatus / RetryPolicy
  - Activity / ActivityContext / ActivityResult / from_callable
  - persistence helpers
"""
from .engine import PGCheckpointerEngine, WorkflowEngine
from .persistence import (
    ActivityHistoryRow,
    Base,
    WorkflowCheckpointRow,
    WorkflowRunRow,
    init_schema,
    make_engine,
    make_session_factory,
)
from .step import (
    Activity,
    ActivityContext,
    ActivityResult,
    CallableActivity,
    RetryPolicy,
    StepMeta,
    StepStatus,
    WorkflowStep,
    from_callable,
)
from .workflow import (
    Query,
    Signal,
    Workflow,
    WorkflowRun,
    WorkflowStatus,
    new_run_id,
)

__all__ = [
    # engine
    "WorkflowEngine",
    "PGCheckpointerEngine",
    # workflow
    "Workflow",
    "WorkflowRun",
    "WorkflowStatus",
    "Signal",
    "Query",
    "new_run_id",
    # step
    "WorkflowStep",
    "StepMeta",
    "StepStatus",
    "RetryPolicy",
    # activity
    "Activity",
    "ActivityContext",
    "ActivityResult",
    "CallableActivity",
    "from_callable",
    # persistence
    "Base",
    "WorkflowRunRow",
    "WorkflowCheckpointRow",
    "ActivityHistoryRow",
    "init_schema",
    "make_engine",
    "make_session_factory",
]
