"""skill_usage.py — Phase C C006 Skill Usage Tracker.

Records every invocation of every skill so the kernel can:

  - compute per-skill success rates (track + success_rate)
  - find skill deprecation candidates (deprecate_candidates)
  - gate canary deployments (C008 will read get_calls since a ts)
  - feed the learning loop (C009/C011)

Design contract (C006 spec §Scope):

  - `SkillUsage` is the *aggregated* per-skill record:
        skill_id, used_at, success_count, failure_count, context_hash
    `used_at` is the timestamp of the MOST RECENT invocation.
    `context_hash` is the hash of the most recent invocation context
    (the kernel uses this to know whether a skill is being called in
    the same context as before or in a new one — important for
    detecting context-drift regressions).

  - `SkillUsageAudit` is the *per-call* record (one per track() call):
        skill_id, used_at, success, context_hash
    The audit log is the source of truth for "did every call get
    captured?" — required by the C006 evidence checklist ("5 skills
    x 100 task = 500 calls 全数 captured"). Aggregates can always be
    rebuilt from the audit log; the aggregates are an index for fast
    queries.

  - `track(skill_id, success, *, context_hash=None)`:
        MUST write an audit row (no silent track) — the spec explicitly
        forbids silent track (Forbidden section of C006 card).
        MUST also write a kernel log line via the `skill_usage` logger
        so the operator can grep for usage events.
        MUST also update (or create) the aggregated `SkillUsage` row.

  - `get_usage(skill_id, since)` returns the aggregate whose
        used_at >= since (None if missing / too old).

  - `get_calls(skill_id, since)` returns the per-call audit rows in
        insertion order. Used by C007 deprecation detector and by the
        C006 evidence "5 skills x 100 task = 500 calls" check.

  - `success_rate(skill_id, since)` returns a float in [0.0, 1.0]
        over the filtered call set; returns 0.0 if there are no calls.

  - `deprecate_candidates(unused_days=30, max_failure_rate=0.5,
                           min_calls=1, as_of=None)` returns aggregated
        rows that EITHER have not been used in `unused_days` OR have a
        failure rate >= `max_failure_rate` (>= 50% by default). The
        caller is C007 (Skill Deprecation).

  - `format(usage)` renders a single-line human-readable summary used
        for CLI inspection / evidence prints.

In-process, in-memory storage. Persistence is OUT of scope for C006 —
the trace data already lives in the durable `traces` table (T0033)
and the C002 trace-miner is responsible for bridging usage events into
durable history. The in-memory design is sufficient for the card's
evidence requirements (5 x 100 calls captured during a single test
process) and keeps C007/C008 unblocked.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope, utcnow

# Module-level logger so every track() call leaves a non-silent audit
# trail in the kernel log. C006 spec §Forbidden: "静默 track (无 audit
# log)" — this logger is the contract that track() will use.
logger = logging.getLogger("aios_kernel.learning.skill_usage")


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Coerce a datetime to tz-aware UTC (None passes through)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class SkillUsage(Envelope):
    """Aggregated usage record for ONE skill (one row per skill_id).

    Inherits id / created_at / updated_at / schema_version from Envelope.

    `created_at` records when the skill was first tracked.
    `updated_at` records the last time this aggregate was mutated.
    `used_at` records the timestamp of the most recent invocation
    (which may be different from updated_at when, e.g., the aggregate
    is loaded from cache before being checked).

    Invariants enforced by the service (not the model — so the model
    stays cheap to construct):

      - success_count + failure_count == number of `track()` calls for
        this skill_id since the aggregate was created.
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    skill_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Skill identifier (matches the capability_registry skill_id).",
    )
    used_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp of the most recent invocation.",
    )
    success_count: int = Field(
        default=0,
        ge=0,
        description="Number of successful invocations since aggregate was created.",
    )
    failure_count: int = Field(
        default=0,
        ge=0,
        description="Number of failed invocations since aggregate was created.",
    )
    context_hash: str | None = Field(
        default=None,
        max_length=128,
        description=(
            "Hash of the most recent invocation context. Lets callers detect "
            "context-drift (skill is being called in a new context)."
        ),
    )

    @field_validator("used_at")
    @classmethod
    def _used_at_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("used_at must be tz-aware (use envelope.utcnow())")
        return v.astimezone(UTC)

    # ---------- helpers -----------------------------------------------------

    def total_calls(self) -> int:
        """Total number of invocations captured by this aggregate."""
        return self.success_count + self.failure_count

    def success_rate(self) -> float:
        """Return success_count / total_calls in [0, 1]; 0.0 if no calls."""
        total = self.total_calls()
        if total == 0:
            return 0.0
        return self.success_count / total


class SkillUsageAudit(Envelope):
    """One record per `track()` call (append-only audit log).

    Inherits id / created_at / updated_at / schema_version from Envelope.

    `created_at` is the audit row's creation time (== track() call time
    on a well-behaved clock). The audit log is the source of truth
    for "did every call get captured?" — it is NEVER trimmed by the
    tracker (callers may archive / persist it externally).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    skill_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Skill identifier (matches the aggregate).",
    )
    used_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp of THIS invocation.",
    )
    success: bool = Field(
        ...,
        description="True iff the invocation succeeded.",
    )
    context_hash: str | None = Field(
        default=None,
        max_length=128,
        description="Hash of the invocation context (caller-supplied).",
    )

    @field_validator("used_at")
    @classmethod
    def _used_at_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("used_at must be tz-aware (use envelope.utcnow())")
        return v.astimezone(UTC)


class SkillUsageTracker:
    """In-memory tracker for skill usage (C006).

    Public surface:
        await tracker.track(skill_id, success, *, context_hash=None)
        tracker.get_usage(skill_id, since=None) -> SkillUsage | None
        tracker.get_all_usage(since=None) -> list[SkillUsage]
        tracker.get_calls(skill_id=None, since=None) -> list[SkillUsageAudit]
        tracker.success_rate(skill_id, since=None) -> float
        tracker.deprecate_candidates(unused_days=30, max_failure_rate=0.5,
                                     min_calls=1, as_of=None) -> list[SkillUsage]
        tracker.format(usage) -> str
        tracker.audit_log -> list[SkillUsageAudit]   (read-only snapshot)
        tracker.aggregates -> dict[str, SkillUsage]  (read-only snapshot)

    Concurrency model: single-process, single-threaded. The kernel
    wraps this service with a lock if it ever needs cross-async-task
    safety; the card does not require it (all callers in C006 tests are
    sequential).
    """

    def __init__(self) -> None:
        self._usage: dict[str, SkillUsage] = {}
        self._audit: list[SkillUsageAudit] = []

    # ---------- read-only snapshots ----------------------------------------

    @property
    def audit_log(self) -> list[SkillUsageAudit]:
        """Read-only snapshot of the full audit log (insertion order)."""
        return list(self._audit)

    @property
    def aggregates(self) -> dict[str, SkillUsage]:
        """Read-only snapshot of the per-skill aggregates."""
        return dict(self._usage)

    # ---------- write ------------------------------------------------------

    async def track(
        self,
        skill_id: str,
        success: bool,
        *,
        context_hash: str | None = None,
    ) -> SkillUsage:
        """Record one skill invocation. NEVER silent — writes:

        1. One `SkillUsageAudit` row appended to the audit log.
        2. One `logging.info` line on `aios_kernel.learning.skill_usage`
           (so the operator can grep the kernel log for usage events).
        3. Update (or create) the `SkillUsage` aggregate for `skill_id`.

        Returns the (possibly newly created) aggregate.
        """
        if not skill_id or not isinstance(skill_id, str):
            raise ValueError("skill_id must be a non-empty string")

        now = utcnow()
        # 1. Mandatory audit entry.
        audit = SkillUsageAudit(
            skill_id=skill_id,
            used_at=now,
            success=bool(success),
            context_hash=context_hash,
        )
        self._audit.append(audit)

        # 2. Mandatory non-silent kernel log line. The level is INFO
        #    because per-call log volume is bounded by call rate; the
        #    message includes the skill_id so log greps work.
        logger.info(
            "skill_usage.track skill_id=%s success=%s audit_id=%s",
            skill_id,
            success,
            audit.id,
        )

        # 3. Update (or create) the aggregate.
        existing = self._usage.get(skill_id)
        if existing is None:
            agg = SkillUsage(
                skill_id=skill_id,
                used_at=audit.used_at,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                context_hash=context_hash,
            )
            self._usage[skill_id] = agg
        else:
            if success:
                existing.success_count += 1
            else:
                existing.failure_count += 1
            existing.used_at = audit.used_at
            existing.context_hash = context_hash
            existing.touch()
            agg = existing
        return agg

    # ---------- reads -------------------------------------------------------

    def get_usage(
        self,
        skill_id: str,
        since: datetime | None = None,
    ) -> SkillUsage | None:
        """Return the aggregate for `skill_id` if `used_at >= since`.

        Returns None if the skill was never tracked OR if its most
        recent invocation is older than `since`.
        """
        usage = self._usage.get(skill_id)
        if usage is None:
            return None
        if since is not None:
            since = _ensure_utc(since)
            if usage.used_at < since:
                return None
        return usage

    def get_all_usage(self, since: datetime | None = None) -> list[SkillUsage]:
        """Return all aggregates whose `used_at >= since`.

        Empty list if `since` filters everything out. Order is not
        specified (callers should sort if they need determinism).
        """
        if since is None:
            return list(self._usage.values())
        since = _ensure_utc(since)
        return [u for u in self._usage.values() if u.used_at >= since]

    def get_calls(
        self,
        skill_id: str | None = None,
        since: datetime | None = None,
    ) -> list[SkillUsageAudit]:
        """Return audit rows, optionally filtered by skill_id / since.

        Insertion order is preserved (oldest first). `skill_id=None`
        means "all skills"; `since=None` means "all time".
        """
        if since is not None:
            since = _ensure_utc(since)
        out: list[SkillUsageAudit] = []
        for row in self._audit:
            if skill_id is not None and row.skill_id != skill_id:
                continue
            if since is not None and row.used_at < since:
                continue
            out.append(row)
        return out

    def success_rate(
        self,
        skill_id: str,
        since: datetime | None = None,
    ) -> float:
        """Return success_count / call_count over the filtered audit set.

        Returns 0.0 if the filtered set is empty (no evidence of
        success OR failure — caller should treat 0.0 as "unknown").
        """
        calls = self.get_calls(skill_id, since=since)
        if not calls:
            return 0.0
        ok = sum(1 for c in calls if c.success)
        return ok / len(calls)

    # ---------- analysis ---------------------------------------------------

    def deprecate_candidates(
        self,
        *,
        unused_days: int = 30,
        max_failure_rate: float = 0.5,
        min_calls: int = 1,
        as_of: datetime | None = None,
    ) -> list[SkillUsage]:
        """Return aggregates considered for deprecation.

        A skill is a candidate iff EITHER:

          (a) It has not been used for >= `unused_days` as of `as_of`
              (default = now). I.e. used_at < as_of - unused_days.

          (b) Its success_rate is <= (1.0 - max_failure_rate) AND
              it has at least `min_calls` calls (to avoid deprecating a
              brand-new skill on its first failure).

        Both criteria are evaluated; duplicates (a skill matching both)
        are deduplicated by skill_id. The result is sorted by
        `skill_id` for determinism.
        """
        if unused_days < 0:
            raise ValueError("unused_days must be >= 0")
        if not 0.0 <= max_failure_rate <= 1.0:
            raise ValueError("max_failure_rate must be in [0, 1]")
        if min_calls < 1:
            raise ValueError("min_calls must be >= 1")

        cutoff = _ensure_utc(as_of) or utcnow()
        unused_cutoff = cutoff - timedelta(days=unused_days)
        seen: dict[str, SkillUsage] = {}
        for usage in self._usage.values():
            calls = self.get_calls(usage.skill_id)
            if len(calls) < min_calls:
                continue
            unused = usage.used_at < unused_cutoff
            failing = usage.success_rate() <= (1.0 - max_failure_rate)
            if unused or failing:
                seen[usage.skill_id] = usage
        return [seen[k] for k in sorted(seen.keys())]

    # ---------- formatting -------------------------------------------------

    @staticmethod
    def format(usage: SkillUsage) -> str:
        """Render a single-line human-readable summary.

        Format:
            SkillUsage(skill_id=<id>, used_at=<iso8601>, success=<n>,
                       failure=<n>, total=<n>, success_rate=<pct>,
                       context_hash=<hash-or-None>)
        """
        used_at_iso = usage.used_at.astimezone(UTC).isoformat()
        rate_pct = f"{usage.success_rate() * 100:.2f}%"
        return (
            f"SkillUsage(skill_id={usage.skill_id}, "
            f"used_at={used_at_iso}, "
            f"success={usage.success_count}, "
            f"failure={usage.failure_count}, "
            f"total={usage.total_calls()}, "
            f"success_rate={rate_pct}, "
            f"context_hash={usage.context_hash})"
        )

    # ---------- introspection ----------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return (
                f"SkillUsageTracker(skills={len(self._usage)}, "
                f"audit_rows={len(self._audit)})"
        )


__all__ = [
    "SkillUsage",
    "SkillUsageAudit",
    "SkillUsageTracker",
]
