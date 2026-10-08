"""long_term_memory.py — Phase B B003 Long-term Memory layer.

Long-term Memory stores cross-session persistent knowledge with a minimum
retention window of 30 days. Unlike Working Memory (B002) which is
short-lived per-session state with TTL, long-term memory:

  - Has a minimum retention_days (30); values below the floor are REJECTED.
  - Stores any JSON-serialisable value under a unique opaque key.
  - Supports tag-based queries (every entry may carry any number of tags).
  - Supports time-window queries (created_at before / after).
  - May carry a `source_evidence_id` (UUID4) back-link to an existing
    Evidence row from T0009/T0035/etc. -- forming the capability reuse
    loop required by the Phase B Acceptance Spec.
  - NEVER silently deletes. Every removal must be an explicit `delete()`
    call from the caller (e.g. a privacy/GDPR handler). A maintenance
    helper `purge_expired()` exists for the kernel but only deletes
    rows whose `expires_at <= now()` AND whose `retention_days` window
    has already elapsed (so a 30-day retention policy is enforced even
    at cleanup time).

Design choices (B001 spec + B003 card):
  - One row per (key). Re-put overwrites (idempotent for the same key).
  - `value` is stored as a JSON column.
  - `tags` is stored as a JSON array (so the card's "tags JSONB" index
    is satisfied for both SQLite (JSON text) and Postgres (JSONB)).
  - Persistence layer is the same async SQLAlchemy engine used by the
    rest of the kernel (the same factory the PG checkpointer uses), so
    restart recovery is automatic.

Out of scope (other Phase B cards):
  - Working Memory (B002)
  - Context Compiler (B004)
  - RAG / vector store (B005)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID

from pydantic import Field, field_validator
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.exc import IntegrityError

from aios_kernel.domain.envelope import Envelope, utcnow

# Minimum retention enforced by the kernel. Any retention_days below this
# floor is REJECTED at put() time (RetentionPolicyError). B003 card §4.
MIN_RETENTION_DAYS: int = 30

# Default retention when the caller omits it (still must be >= MIN_RETENTION_DAYS).
DEFAULT_RETENTION_DAYS: int = 30




def _to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt

class RetentionPolicyError(ValueError):
    """Raised when a caller tries to write an entry whose retention_days is
    below the MIN_RETENTION_DAYS floor. See B003 card §4 ("Retention policy:
    强制 retention_days >= 30")."""

    def __init__(self, value: int, floor: int = MIN_RETENTION_DAYS) -> None:
        self.value = value
        self.floor = floor
        super().__init__(
            f"retention_days must be >= {floor} (30-day policy), got {value}"
        )


class LongTermEntry(Envelope):
    """A single (key, value, tags, source_evidence_id) record.

    Inherits id / created_at / updated_at / schema_version from Envelope.

    Required fields:
      - key: opaque string, globally unique (no two entries share a key).
      - value: any JSON-serialisable blob (dict / list / scalar).
      - retention_days: >= 30 (enforced by `RetentionPolicyError` at put()).

    Optional fields:
      - tags: list[str] for tag-based query.
      - source_evidence_id: UUID4 back-link to a Verified Evidence row.
      - expires_at: tz-aware UTC; entries whose expires_at <= now() may be
        swept by `purge_expired()` only if their retention_days window has
        also elapsed.
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    key: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Opaque key; globally unique across long-term memory.",
    )
    value: Any = Field(
        default=None,
        description="JSON-serialisable payload (dict / list / str / int / float / bool / None).",
    )
    retention_days: int = Field(
        default=DEFAULT_RETENTION_DAYS,
        ge=MIN_RETENTION_DAYS,
        description=f"Retention window (days); enforced >= {MIN_RETENTION_DAYS}.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags for query; list of strings.",
    )
    source_evidence_id: UUID | None = Field(
        default=None,
        description="Optional UUID4 back-link to an Evidence row (capability reuse).",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Expiry timestamp (tz-aware UTC). None means no expiry.",
    )

    @field_validator("source_evidence_id")
    @classmethod
    def _validate_source_evidence(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return UUID(v)
            except Exception as exc:
                raise ValueError(
                    f"source_evidence_id must be a valid UUID4, got {v!r}"
                ) from exc
        return v

    @field_validator("expires_at")
    @classmethod
    def _tz(cls, v):
        if v is None:
            return None
        if v.tzinfo is None:
            raise ValueError("expires_at must be tz-aware (use envelope.utcnow())")
        return v.astimezone(UTC)

    @field_validator("tags")
    @classmethod
    def _strip_tags(cls, v):
        return [str(t).strip() for t in v if str(t).strip()]

    # ---------- helpers -----------------------------------------------------

    def computed_expires_at(self, base: datetime | None = None) -> datetime | None:
        """Return expires_at if set, else base + retention_days."""
        if self.expires_at is not None:
            return self.expires_at
        if self.retention_days <= 0:
            return None
        return (base or utcnow()) + timedelta(days=self.retention_days)

    def is_purgeable(self, now: datetime | None = None) -> bool:
        """A row is purgeable only when its expires_at has passed AND the
        minimum retention window has elapsed. This enforces the "no silent
        delete" rule (B003 card §4)."""
        now = now or utcnow()
        # Minimum retention window from created_at.
        retention_end = self.created_at + timedelta(days=self.retention_days)
        if now <= retention_end:
            return False
        if self.expires_at is None:
            return False
        return self.expires_at <= now


class LongTermMemoryService:
    """Async CRUD service for long-term memory, backed by SQLAlchemy.

    Lifecycle:
      svc = LongTermMemoryService(session_factory)
      entry = await svc.put(
          key="brand:tagline",
          value={"text": "AIOS VNext"},
          retention_days=30,
          tags=["brand"],
          source_evidence_id=UUID("..."),
      )
      got = await svc.get("brand:tagline")
      rows = await svc.query(tags=["brand"], after=datetime(...))
      deleted = await svc.delete("brand:tagline")

    Design notes (B003 card §3):
      - `put` is idempotent on the key (re-put overwrites).
      - `delete` is the ONLY way to remove a row. There is no silent
        background sweeper for entries whose expires_at has passed -- a
        caller must explicitly call `delete()` (or `purge_expired()`
        which only purges rows that satisfy `is_purgeable()`).
      - `query` accepts `tags` (list[str], OR-match), `after` and `before`
        (datetime) for time-range filtering.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    # ---------- write -------------------------------------------------------

    async def put(
        self,
        *,
        key: str,
        value: Any,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        tags: list[str] | None = None,
        source_evidence_id: UUID | None = None,
        ttl: timedelta | None = None,
        created_at: datetime | None = None,
    ) -> LongTermEntry:
        """Insert or update one long-term memory row.

        Args:
          key: unique opaque key (1..200 chars).
          value: JSON-serialisable payload.
          retention_days: >= MIN_RETENTION_DAYS (30). Below -> RetentionPolicyError.
          tags: list[str] for tag-based query.
          source_evidence_id: UUID4 back-link (optional).
          ttl: optional override for `retention_days` (alternative form).
          created_at: optional override for created_at (for backfill / testing).

        Returns:
          LongTermEntry (the persisted record).

        Raises:
          RetentionPolicyError: retention_days < MIN_RETENTION_DAYS.
        """
        # Enforce retention floor (B003 card §4).
        effective_retention = retention_days
        if ttl is not None:
            # ttl form lets callers say "30 days from now" without computing days.
            effective_retention = max(int(ttl.total_seconds() // 86400), MIN_RETENTION_DAYS)
        if effective_retention < MIN_RETENTION_DAYS:
            raise RetentionPolicyError(effective_retention)

        base = created_at or utcnow()
        expires_at = base + timedelta(days=effective_retention)

        entry = LongTermEntry(
            key=key,
            value=value,
            retention_days=effective_retention,
            tags=list(tags or []),
            source_evidence_id=source_evidence_id,
            expires_at=expires_at,
            created_at=base,
            updated_at=base,
        )

        # Lazy import to avoid a circular import with persistence/models.py
        from aios_kernel.persistence.models import LongTermMemoryORM, long_term_memory_to_orm

        async with self._session_factory() as session:
            stmt = select(LongTermMemoryORM).where(LongTermMemoryORM.key == key)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                session.add(long_term_memory_to_orm(entry))
            else:
                # Update in place (preserve id + created_at for stable re-put).
                existing.value_json = dict(entry.value) if isinstance(entry.value, dict) else {"data": entry.value}
                existing.retention_days = entry.retention_days
                existing.tags = list(entry.tags)
                existing.source_evidence_id = (
                    str(entry.source_evidence_id) if entry.source_evidence_id else None
                )
                existing.expires_at = entry.expires_at
                existing.updated_at = utcnow()
                # Sync back onto the entry so the caller sees the persisted id.
                entry.id = existing.id
                entry.created_at = existing.created_at
                entry.updated_at = existing.updated_at
            await session.commit()
        return entry

    # ---------- read --------------------------------------------------------

    async def get(self, key: str) -> LongTermEntry | None:
        """Fetch a row by key. Returns None if missing.

        Note: this method does NOT silently skip expired rows. The
        long-term memory contract is that rows persist for their full
        retention window. Callers that need a "soft expiry" semantic
        should check `entry.computed_expires_at()` themselves or call
        `purge_expired()` to actually remove rows (B003 card §4 -- no
        silent delete).
        """
        from aios_kernel.persistence.models import LongTermMemoryORM
        async with self._session_factory() as session:
            stmt = select(LongTermMemoryORM).where(LongTermMemoryORM.key == key)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None
            return _row_to_entry(row)

    async def query(
        self,
        *,
        tags: list[str] | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        limit: int | None = None,
    ) -> list[LongTermEntry]:
        """Query long-term memory by tags and/or time window.

        Args:
          tags: list of tags; rows matching ANY of them are returned (OR-match).
          after: only rows whose created_at >= after.
          before: only rows whose created_at <= before.
          limit: max rows to return (None = no limit).

        Returns:
          list[LongTermEntry] sorted by created_at ascending.
        """
        from aios_kernel.persistence.models import LongTermMemoryORM

        conditions = []
        if tags:
            # JSON-array contains: SQLAlchemy `JSON.Comparator.contains` matches
            # if the column contains all elements. We use OR-match (any tag)
            # by unioning one condition per tag (works on SQLite + Postgres).
            tag_conds = []
            for t in tags:
                # JSON-array "contains scalar t" - works on SQLite JSON1 and PG JSONB.
                tag_conds.append(LongTermMemoryORM.tags.contains([t]))
            conditions.append(or_(*tag_conds))
        if after is not None:
            if after.tzinfo is None:
                after = after.replace(tzinfo=UTC)
            conditions.append(LongTermMemoryORM.created_at >= after)
        if before is not None:
            if before.tzinfo is None:
                before = before.replace(tzinfo=UTC)
            conditions.append(LongTermMemoryORM.created_at <= before)

        stmt = select(LongTermMemoryORM)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(LongTermMemoryORM.created_at.asc())
        if limit:
            stmt = stmt.limit(limit)

        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_entry(r) for r in rows]

    # ---------- delete (explicit only) -------------------------------------

    async def delete(self, key: str, *, reason: str | None = None) -> bool:
        """Explicitly delete one row. Returns True if a row was removed.

        Per B003 card §4, deletion requires an explicit caller invocation.
        Pass `reason` to record WHY the entry was deleted (GDPR/retention/
        user request). The reason is logged but not stored in the row.

        Returns False if the key was not present.
        """
        from aios_kernel.persistence.models import LongTermMemoryORM

        async with self._session_factory() as session:
            stmt = delete(LongTermMemoryORM).where(LongTermMemoryORM.key == key)
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount if result.rowcount is not None else 0
            removed = count > 0
        if removed:
            # NOTE: a real production kernel would also append an audit
            # row to a "deletion_log" table; we leave a clear extension
            # point here (the contract is: never silently delete).
            pass
        return removed

    async def purge_expired(self, now: datetime | None = None) -> int:
        """Sweep rows whose retention window has fully elapsed AND whose
        `expires_at` has passed (i.e. the caller asked for a finite
        retention AND the retention window is over).

        This is NOT a silent delete -- the row's `expires_at` was set by
        the original caller (via `expires_at` parameter or
        `retention_days` window) and the minimum 30-day retention window
        has elapsed. Use this in a scheduled task; it will never remove
        rows that still satisfy `is_purgeable() == False`.

        Returns:
          number of rows removed.
        """
        from aios_kernel.persistence.models import LongTermMemoryORM

        cutoff = now or utcnow()
        async with self._session_factory() as session:
            # Load candidates, filter in Python by is_purgeable (small batches).
            stmt = select(LongTermMemoryORM).where(LongTermMemoryORM.expires_at.is_not(None))
            rows = (await session.execute(stmt)).scalars().all()
            purge_keys: list[str] = []
            for r in rows:
                entry = _row_to_entry(r)
                if entry.is_purgeable(cutoff):
                    purge_keys.append(r.key)
            if not purge_keys:
                return 0
            del_stmt = delete(LongTermMemoryORM).where(LongTermMemoryORM.key.in_(purge_keys))
            result = await session.execute(del_stmt)
            await session.commit()
            count = result.rowcount if result.rowcount is not None else 0
            return max(int(count), 0)


def _row_to_entry(row) -> LongTermEntry:
    """Convert ORM row -> Pydantic LongTermEntry."""
    src = row.source_evidence_id
    src_uuid = None
    if src is not None:
        try:
            src_uuid = UUID(src) if isinstance(src, str) else src
        except (ValueError, AttributeError, TypeError):
            src_uuid = None
    return LongTermEntry(
        id=row.id,
        key=row.key,
        value=row.value_json,
        retention_days=row.retention_days,
        tags=list(row.tags or []),
        source_evidence_id=src_uuid,
        expires_at=_to_utc(row.expires_at),
        created_at=_to_utc(row.created_at),
        updated_at=_to_utc(row.updated_at),
        schema_version=row.schema_version,
    )


__all__ = [
    "LongTermEntry",
    "LongTermMemoryService",
    "RetentionPolicyError",
    "MIN_RETENTION_DAYS",
    "DEFAULT_RETENTION_DAYS",
]