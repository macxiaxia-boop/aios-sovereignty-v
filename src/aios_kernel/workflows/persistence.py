"""persistence.py - PG checkpointer: 3 tables for durable execution (T0033).

Tables:
  - workflow_runs        (one row per run)
  - workflow_checkpoints (one row per completed step; basis for restart)
  - activity_history     (one row per attempt; audit trail)

Engine = SQLAlchemy 2.0 async. Works with:
  - sqlite+aiosqlite:// (dev / test)
  - postgresql+asyncpg:// (prod)
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
    select,
    update,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------- ORM base --------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------- Tables ----------------------------------------------------------


class WorkflowRunRow(Base):
    __tablename__ = "workflow_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    current_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class WorkflowCheckpointRow(Base):
    __tablename__ = "workflow_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ActivityHistoryRow(Base):
    __tablename__ = "activity_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    activity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # started/completed/failed/retried
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowLeaseRow(Base):
    """Independent additive table; init_schema(create_all) preserves old runs."""

    __tablename__ = "workflow_leases"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    fencing_token: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class WorkflowEffectRow(Base):
    """Persist side effect dispatch before calling remote provider."""

    __tablename__ = "workflow_effects"

    effect_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="prepared")
    receipt_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reconciliation_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------- Engine factory --------------------------------------------------



def make_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Dev / test: ``sqlite+aiosqlite:///./kernel.db``
    Prod:       ``postgresql+asyncpg://user:pw@host:5432/aios``
    """
    # echo=False to keep test output clean; flip to True for SQL trace
    return create_async_engine(database_url, echo=False, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_schema(engine: AsyncEngine) -> None:
    """Create all tables. Idempotent — safe to call multiple times."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_schema(engine: AsyncEngine) -> None:
    """Drop all tables. Test-only helper."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)




# ---------- External side-effect journal ------------------------------------


async def prepare_external_effect(
    session: AsyncSession,
    *,
    effect_key: str,
    run_id: str,
    step_id: str,
    request_hash: str,
) -> WorkflowEffectRow:
    """Persistent stable request identity; conflict with changed payload is fatal."""
    dialect_insert = _insert_for_dialect(session)
    await session.execute(
        dialect_insert(WorkflowEffectRow)
        .values(
            effect_key=effect_key, run_id=run_id, step_id=step_id,
            request_hash=request_hash, status="prepared",
            receipt_json={},
        )
        .on_conflict_do_nothing(index_elements=["effect_key"])
    )
    row = await session.get(WorkflowEffectRow, effect_key)
    if row is None:
        raise RuntimeError("effect not visible after journal insert")
    if (row.run_id, row.step_id, row.request_hash) != (run_id, step_id, request_hash):
        raise ValueError("external effect key reused with conflicting operation")
    return row


async def transition_external_effect(
    session: AsyncSession,
    *,
    effect_key: str,
    from_status: str,
    to_status: str,
    receipt: dict[str, Any] | None = None,
    reconciliation_evidence: str | None = None,
) -> bool:
    """Single-writer CAS; do not revive sent/unknown operations for blind retry."""
    values: dict[str, Any] = {"status": to_status}
    if receipt is not None:
        values["receipt_json"] = receipt
    if reconciliation_evidence is not None:
        values["reconciliation_evidence"] = reconciliation_evidence
    result = await session.execute(
        update(WorkflowEffectRow)
        .where(WorkflowEffectRow.effect_key == effect_key)
        .where(WorkflowEffectRow.status == from_status)
        .values(**values)
    )
    return result.rowcount == 1


# ---------- Workflow lease / fencing ---------------------------------------


def _insert_for_dialect(session: AsyncSession):
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        raise ValueError(f"unsupported workflow persistence dialect: {dialect}")
    return dialect_insert


async def acquire_workflow_lease(
    session: AsyncSession,
    *,
    run_id: str,
    owner_id: str,
    ttl_s: float = 120.0,
) -> int | None:
    """Acquire via DB atomic UPDATE; return new monotonically increasing fence.

    None means another unexpired owner holds the run. Both SQLite and
    PostgreSQL serialize the conditional UPDATE. Do not put an external
    network call inside this transaction.
    """
    if ttl_s <= 0:
        raise ValueError("workflow lease TTL must be positive")
    now = _now()
    dialect_insert = _insert_for_dialect(session)
    await session.execute(
        dialect_insert(WorkflowLeaseRow)
        .values(run_id=run_id, owner_id="", fencing_token=0, expires_at=now)
        .on_conflict_do_nothing(index_elements=["run_id"])
    )
    stmt = (
        update(WorkflowLeaseRow)
        .where(WorkflowLeaseRow.run_id == run_id)
        .where(WorkflowLeaseRow.expires_at <= now)
        .values(
            owner_id=owner_id,
            fencing_token=WorkflowLeaseRow.fencing_token + 1,
            expires_at=now + timedelta(seconds=ttl_s),
        )
        .returning(WorkflowLeaseRow.fencing_token)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def renew_workflow_lease(
    session: AsyncSession,
    *,
    run_id: str,
    owner_id: str,
    fencing_token: int,
    ttl_s: float = 120.0,
) -> bool:
    """CAS fence check and refresh. Must run in the SAME transaction as checkpoint."""
    if ttl_s <= 0:
        raise ValueError("workflow lease TTL must be positive")
    now = _now()
    stmt = (
        update(WorkflowLeaseRow)
        .where(WorkflowLeaseRow.run_id == run_id)
        .where(WorkflowLeaseRow.owner_id == owner_id)
        .where(WorkflowLeaseRow.fencing_token == fencing_token)
        .where(WorkflowLeaseRow.expires_at > now)
        .values(expires_at=now + timedelta(seconds=ttl_s))
    )
    result = await session.execute(stmt)
    return result.rowcount == 1


async def release_workflow_lease(
    session: AsyncSession,
    *,
    run_id: str,
    owner_id: str,
    fencing_token: int,
) -> bool:
    """Old owner cannot release a successor's lease."""
    stmt = (
        update(WorkflowLeaseRow)
        .where(WorkflowLeaseRow.run_id == run_id)
        .where(WorkflowLeaseRow.owner_id == owner_id)
        .where(WorkflowLeaseRow.fencing_token == fencing_token)
        .values(owner_id="", expires_at=_now())
    )
    result = await session.execute(stmt)
    return result.rowcount == 1


# ---------- Data access helpers --------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


async def insert_run(
    session: AsyncSession,
    *,
    run_id: str,
    workflow_id: str,
    input_json: dict[str, Any],
) -> bool:
    # True only when this request created the run. Required to avoid concurrent
    # first-submit attempts both executing external side effects.
    # Dialect-specific INSERT: SQLite Insert must not be compiled as PostgreSQL.
    # This operation never replays a completed run (see WorkflowEngine.start).
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        raise ValueError(f"unsupported workflow persistence dialect: {dialect}")
    stmt = dialect_insert(WorkflowRunRow).values(
        run_id=run_id,
        workflow_id=workflow_id,
        status="pending",
        current_step=None,
        input_json=input_json,
        output_json={},
        started_at=None,
        completed_at=None,
    ).on_conflict_do_nothing(index_elements=["run_id"])
    result = await session.execute(stmt)
    await session.flush()
    # Both supported backends return 1 for insert and 0 for conflict.
    # The default covers simple test doubles that return no cursor result.
    return getattr(result, "rowcount", 1) == 1


async def update_run(
    session: AsyncSession,
    *,
    run_id: str,
    status: str | None = None,
    current_step: str | None = None,
    output_json: dict[str, Any] | None = None,
    error: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    row = await session.get(WorkflowRunRow, run_id)
    if row is None:
        raise KeyError(f"no run {run_id!r}")
    if status is not None:
        row.status = status
    if current_step is not None:
        row.current_step = current_step
    if output_json is not None:
        row.output_json = output_json
    if error is not None:
        row.error = error
    if started_at is not None:
        row.started_at = started_at
    if completed_at is not None:
        row.completed_at = completed_at
    row.updated_at = _now()
    await session.flush()


async def get_run(session: AsyncSession, run_id: str) -> WorkflowRunRow | None:
    return await session.get(WorkflowRunRow, run_id)


async def list_runs_by_status(
    session: AsyncSession, status: str
) -> list[WorkflowRunRow]:
    stmt = select(WorkflowRunRow).where(WorkflowRunRow.status == status)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def write_checkpoint(
    session: AsyncSession,
    *,
    run_id: str,
    step_id: str,
    step_index: int,
    state_json: dict[str, Any],
    attempt: int,
    status: str = "completed",
) -> None:
    row = WorkflowCheckpointRow(
        run_id=run_id,
        step_id=step_id,
        step_index=step_index,
        state_json=state_json,
        attempt=attempt,
        status=status,
    )
    session.add(row)
    await session.flush()


async def latest_checkpoint(
    session: AsyncSession, run_id: str
) -> WorkflowCheckpointRow | None:
    stmt = (
        select(WorkflowCheckpointRow)
        .where(WorkflowCheckpointRow.run_id == run_id)
        .order_by(WorkflowCheckpointRow.created_at.desc(), WorkflowCheckpointRow.id.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def list_checkpoints(
    session: AsyncSession, run_id: str
) -> Sequence[WorkflowCheckpointRow]:
    stmt = (
        select(WorkflowCheckpointRow)
        .where(WorkflowCheckpointRow.run_id == run_id)
        .order_by(WorkflowCheckpointRow.step_index.asc(), WorkflowCheckpointRow.id.asc())
    )
    res = await session.execute(stmt)
    return res.scalars().all()


async def record_activity(
    session: AsyncSession,
    *,
    run_id: str,
    activity_id: str,
    step_id: str,
    attempt: int,
    status: str,
    error: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> None:
    row = ActivityHistoryRow(
        run_id=run_id,
        activity_id=activity_id,
        step_id=step_id,
        attempt=attempt,
        status=status,
        error=error,
        started_at=started_at or _now(),
        finished_at=finished_at,
    )
    session.add(row)
    await session.flush()


# ---------- Serialization helpers ------------------------------------------


def safe_json_loads(raw: Any) -> dict[str, Any]:
    """Defensive: SQLAlchemy JSON columns already deserialize, but if a
    string slips through (older SQLite), we still want a dict back."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"_value": parsed}
        except json.JSONDecodeError:
            return {"_raw": raw}
    return {"_value": str(raw)}

