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
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
    select,
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


# ---------- Data access helpers --------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


async def insert_run(
    session: AsyncSession,
    *,
    run_id: str,
    workflow_id: str,
    input_json: dict[str, Any],
) -> None:
    # Phase B CR7 idempotency: use ON CONFLICT DO NOTHING
    # (Postgres) / INSERT OR IGNORE (SQLite). Multi-cycle crash/recovery
    # re-calls start() with the same run_id; the first call creates the
    # row, subsequent calls are no-ops.
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    stmt = sqlite_insert(WorkflowRunRow).values(
        run_id=run_id,
        workflow_id=workflow_id,
        status="pending",
        current_step=None,
        input_json=input_json,
        output_json={},
        started_at=None,
        completed_at=None,
    ).on_conflict_do_nothing(index_elements=["run_id"])
    await session.execute(stmt)
    await session.flush()
    return


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
