"""working_memory.py - Phase B B002 Working Memory layer.

Working Memory stores short-lived per-session state for the kernel. It is
the "Phase A T0033 PG checkpointer for activity history" complement: where
the durable checkpointer holds workflow run state across kernel restarts,
working memory holds the per-session working variables (e.g. the current
goal id, the user's last query, scratchpad blobs, conversation memory
slots) that the kernel needs to resume a session after restart.

Design choices (B001 spec + B002 card):
  - One row per (session_id, key). Re-put overwrites (idempotent for the
    same key). Different sessions are isolated by session_id.
  - TTL is per-row: stored as expires_at (tz-aware UTC). Default TTL =
    24h. Reads transparently skip expired rows so a key may "evaporate"
    without an explicit delete.
  - The "value" is a free-form JSON-serialisable blob (dict / list /
    scalar). It is stored as a SQL JSON column.
  - Persistence layer is the existing SQLAlchemy async engine used by
    the rest of the kernel (the same engine the PG checkpointer uses),
    so restart recovery is automatic: rows survive between kernel boots
    because they live in the DB.

Out of scope (other Phase B cards):
  - Long-term memory (B003) - cross-session memory with semantic search
  - Context compiler (B004) - decides what to inject into each LLM call
  - RAG / vector store (B005)
  - Skill registry (B006)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from pydantic import Field, field_validator
from sqlalchemy import and_, delete, select

from aios_kernel.domain.envelope import Envelope, utcnow
from aios_kernel.persistence.models import WorkingMemoryORM, working_memory_to_orm

# Default TTL = 24h (per B002 card §Scope item 3).
DEFAULT_TTL: timedelta = timedelta(hours=24)


class WorkingMemoryEntry(Envelope):
    """A single (key, value) pair scoped to a session.

    Inherits id / created_at / updated_at / schema_version from Envelope.

    Required fields:
      - key: opaque string, unique within (session_id, key).
      - value: any JSON-serialisable blob (dict, list, str, int, ...).
      - session_id: groups entries by user / agent session.

    Optional fields:
      - expires_at: tz-aware UTC; rows whose expires_at <= now() are
        treated as missing by get() / list_keys().
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    key: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Opaque key; unique within (session_id, key).",
    )
    value: Any = Field(
        default=None,
        description="JSON-serialisable payload (dict / list / str / int / float / bool / None).",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Owning session identifier (groups entries for isolation).",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Expiry timestamp (tz-aware UTC). None means no expiry.",
    )

    @field_validator("expires_at")
    @classmethod
    def _tz(cls, v):
        if v is None:
            return None
        if v.tzinfo is None:
            raise ValueError("expires_at must be tz-aware (use envelope.utcnow())")
        return v.astimezone(UTC)

    # ---------- helpers -----------------------------------------------------

    def is_expired(self, now: datetime | None = None) -> bool:
        """True if the entry is past expires_at (relative to `now`)."""
        if self.expires_at is None:
            return False
        return self.expires_at <= (now or utcnow())

    @staticmethod
    def default_expiry(ttl: timedelta | None = None) -> datetime:
        """Compute the default expires_at = utcnow() + ttl (default = 24h)."""
        return utcnow() + (ttl or DEFAULT_TTL)


class WorkingMemoryService:
    """Async CRUD service for working memory, backed by SQLAlchemy.

    Lifecycle:
      svc = WorkingMemoryService(session_factory)
      await svc.put("sess-1", "current_goal", {"id": "g-123"})
      entry = await svc.get("sess-1", "current_goal")
      keys  = await svc.list_keys("sess-1")
      n     = await svc.clear_session("sess-1")

    The service takes an async_sessionmaker (the same factory used by
    SqlAlchemyRepository and PGCheckpointerEngine) so a kernel restart
    that constructs a fresh engine pointing at the same DB file / DB
    server will recover the rows already written.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    # ---------- write -------------------------------------------------------

    async def put(
        self,
        session_id: str,
        key: str,
        value: Any,
        *,
        ttl: timedelta | None = DEFAULT_TTL,
    ) -> WorkingMemoryEntry:
        """Insert or overwrite (session_id, key) with the given value.

        TTL semantics:
          - ttl=None and expires_at None -> no expiry (never expires)
          - ttl=timedelta(seconds=0)    -> already expired (rare, useful for tests)
          - ttl=DEFAULT_TTL (24h)       -> standard short-term memory
          - ttl=timedelta(hours=1)      -> short-lived scratchpad
        """
        expires_at: datetime | None
        if ttl is None:
            expires_at = None
        else:
            expires_at = utcnow() + ttl

        entry = WorkingMemoryEntry(
            key=key,
            value=value,
            session_id=session_id,
            expires_at=expires_at,
        )

        async with self._session_factory() as session:
            # Upsert: if (session_id, key) exists, replace it; else insert.
            stmt = select(WorkingMemoryORM).where(
                and_(
                    WorkingMemoryORM.session_id == session_id,
                    WorkingMemoryORM.key == key,
                )
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                session.add(working_memory_to_orm(entry))
            else:
                existing.value_json = entry.value
                existing.expires_at = entry.expires_at
                existing.updated_at = utcnow()
            await session.commit()
        return entry

    # ---------- read --------------------------------------------------------

    async def get(self, session_id: str, key: str) -> WorkingMemoryEntry | None:
        """Fetch (session_id, key) or return None if missing / expired."""
        async with self._session_factory() as session:
            row = await self._fetch_row(session, session_id, key)
            if row is None:
                return None
            return _row_to_entry(row)

    async def list_keys(self, session_id: str) -> list[str]:
        """Return the (non-expired) keys for a session, sorted lexicographically."""
        now = utcnow()
        async with self._session_factory() as session:
            stmt = (
                select(WorkingMemoryORM.key)
                .where(WorkingMemoryORM.session_id == session_id)
                .where(
                    (WorkingMemoryORM.expires_at.is_(None))
                    | (WorkingMemoryORM.expires_at > now)
                )
                .order_by(WorkingMemoryORM.key.asc())
            )
            rows = (await session.execute(stmt)).scalars().all()
            return list(rows)

    # ---------- delete ------------------------------------------------------

    async def clear_session(self, session_id: str) -> int:
        """Delete all entries for a session (including expired ones).

        Returns the number of rows removed.
        """
        async with self._session_factory() as session:
            stmt = delete(WorkingMemoryORM).where(
                WorkingMemoryORM.session_id == session_id
            )
            result = await session.execute(stmt)
            await session.commit()
            # rowcount may be -1 for some dialects (SQLite historically);
            # use raw count for portability.
            count = result.rowcount if result.rowcount is not None else 0
            if count < 0:
                # SQLite fallback: count before delete
                count_stmt = select(WorkingMemoryORM.key).where(
                    WorkingMemoryORM.session_id == session_id
                )
                # (we already deleted, so count of remaining = 0;
                #  return 0 for safety)
                return 0
            return int(count)

    async def cleanup_expired(self, now: datetime | None = None) -> int:
        """Delete all rows whose expires_at <= now(). Returns deleted count.

        Optional maintenance helper - the kernel can run this periodically
        to keep the table small.
        """
        cutoff = now or utcnow()
        async with self._session_factory() as session:
            stmt = delete(WorkingMemoryORM).where(
                WorkingMemoryORM.expires_at <= cutoff
            )
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount if result.rowcount is not None else 0
            return max(int(count), 0)

    # ---------- helpers -----------------------------------------------------

    @staticmethod
    async def _fetch_row(session, session_id: str, key: str) -> WorkingMemoryEntry | None:
        stmt = select(WorkingMemoryORM).where(
            and_(
                WorkingMemoryORM.session_id == session_id,
                WorkingMemoryORM.key == key,
            )
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        exp = row.expires_at
        if exp is not None and exp.tzinfo is None:
            from datetime import UTC
            exp = exp.replace(tzinfo=UTC)
        if exp is not None and exp <= utcnow():
            return None
        return _row_to_entry(row)


def _row_to_entry(row: WorkingMemoryORM) -> WorkingMemoryEntry:
    """Convert ORM row -> Pydantic WorkingMemoryEntry."""
    return WorkingMemoryEntry(
        id=row.id,
        key=row.key,
        value=row.value_json,
        session_id=row.session_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        expires_at=row.expires_at,
        schema_version=row.schema_version,
    )


__all__ = [
    "WorkingMemoryEntry",
    "WorkingMemoryService",
    "DEFAULT_TTL",
]
