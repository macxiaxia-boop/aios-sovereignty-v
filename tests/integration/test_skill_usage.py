"""test_skill_usage.py — Phase C C006 Skill Usage Tracker integration test.

5 required cases (C006 spec §Scope item 4):
    test_track_basic
    test_get_usage_time_range
    test_success_rate
    test_deprecate_candidate
    test_format

Plus 1 evidence-grade case that mirrors the C006 evidence checklist
("5 skills x 100 task = 500 calls 全数 captured"):
    test_500_calls_all_captured

Time-range manipulation note:
    The aggregate's `used_at` and the audit row's `used_at` are set
    separately. `get_usage()` filters on the aggregate; `get_calls()`
    filters on each audit row. Both fields can be back-dated via direct
    attribute assignment (the Pydantic model allows it because `used_at`
    has no frozen / immutability constraint).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aios_kernel.learning.skill_usage import (
    SkillUsage,
    SkillUsageAudit,
    SkillUsageTracker,
)


# ---------------------------------------------------------------------------
# 1. track_basic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_track_basic():
    """track() creates an aggregate on first call and updates it after."""
    tracker = SkillUsageTracker()

    # First track creates the aggregate.
    agg1 = await tracker.track("skill_basic_a", success=True)
    assert isinstance(agg1, SkillUsage)
    assert agg1.skill_id == "skill_basic_a"
    assert agg1.success_count == 1
    assert agg1.failure_count == 0
    assert agg1.context_hash is None
    assert agg1.total_calls() == 1
    assert agg1.success_rate() == pytest.approx(1.0)

    # Subsequent tracks update the SAME aggregate.
    await tracker.track("skill_basic_a", success=False)
    agg3 = await tracker.track("skill_basic_a", success=True)
    assert agg3.skill_id == "skill_basic_a"
    assert agg3.success_count == 2
    assert agg3.failure_count == 1
    assert agg3.total_calls() == 3
    assert agg3.success_rate() == pytest.approx(2 / 3)

    # The audit log has 3 rows (no silent track).
    audit = tracker.audit_log
    assert len(audit) == 3
    assert all(isinstance(row, SkillUsageAudit) for row in audit)
    assert [r.success for r in audit] == [True, False, True]

    # track() also supports context_hash (callers pass it through).
    await tracker.track(
        "skill_basic_b", success=True, context_hash="ctx-abc-123"
    )
    u = tracker.get_usage("skill_basic_b")
    assert u is not None
    assert u.context_hash == "ctx-abc-123"


# ---------------------------------------------------------------------------
# 2. get_usage_time_range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage_time_range():
    """get_usage(skill_id, since) and get_calls(skill_id, since) filter on time."""
    tracker = SkillUsageTracker()
    await tracker.track("skill_tr_a", success=True)

    # Push both aggregate and audit row used_at back by 10 days.
    u = tracker.get_usage("skill_tr_a")
    assert u is not None
    old_ts = datetime.now(UTC) - timedelta(days=10)
    u.used_at = old_ts
    audit_rows = tracker.get_calls("skill_tr_a")
    assert len(audit_rows) == 1
    audit_rows[0].used_at = old_ts

    now = datetime.now(UTC)
    # since = 5 days ago -> used_at is older -> return None
    assert tracker.get_usage("skill_tr_a", since=now - timedelta(days=5)) is None
    # since = 15 days ago -> used_at is newer -> return aggregate
    assert tracker.get_usage("skill_tr_a", since=now - timedelta(days=15)) is not None

    # get_all_usage with since filters per-skill used_at
    await tracker.track("skill_tr_b", success=True)  # fresh
    out = tracker.get_all_usage(since=now - timedelta(days=5))
    ids = {x.skill_id for x in out}
    assert "skill_tr_b" in ids
    assert "skill_tr_a" not in ids

    # get_calls filters per-call used_at
    calls = tracker.get_calls("skill_tr_a", since=now - timedelta(days=15))
    assert len(calls) == 1
    calls_old = tracker.get_calls("skill_tr_a", since=now - timedelta(days=5))
    assert calls_old == []

    # since=None returns everything
    assert len(tracker.get_calls()) == 2


# ---------------------------------------------------------------------------
# 3. success_rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_rate():
    """success_rate = success / total over the filtered audit set."""
    tracker = SkillUsageTracker()

    # 8 success + 2 failure = 0.8
    for _ in range(8):
        await tracker.track("skill_sr", success=True)
    for _ in range(2):
        await tracker.track("skill_sr", success=False)

    rate = tracker.success_rate("skill_sr")
    assert rate == pytest.approx(0.8)

    # Aggregate exposes the same number via success_rate().
    u = tracker.get_usage("skill_sr")
    assert u is not None
    assert u.success_rate() == pytest.approx(0.8)

    # Empty history -> 0.0 (caller treats 0.0 as unknown).
    assert tracker.success_rate("never_seen") == 0.0

    # success_rate with since= cuts off old calls (back-date the audit rows).
    await tracker.track("skill_sr2", success=True)
    u2 = tracker.get_usage("skill_sr2")
    assert u2 is not None
    old_ts = datetime.now(UTC) - timedelta(days=1)
    u2.used_at = old_ts
    audit_rows2 = tracker.get_calls("skill_sr2")
    assert len(audit_rows2) == 1
    audit_rows2[0].used_at = old_ts

    rate_recent = tracker.success_rate("skill_sr2", since=old_ts - timedelta(hours=1))
    rate_future = tracker.success_rate("skill_sr2", since=old_ts + timedelta(hours=1))
    assert rate_recent == pytest.approx(1.0)
    assert rate_future == 0.0


# ---------------------------------------------------------------------------
# 4. deprecate_candidate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deprecate_candidate():
    """deprecate_candidates() flags high-failure and long-unused skills."""
    tracker = SkillUsageTracker()

    # Failing skill: 1 success, 9 failures -> failure_rate = 90% >= 50%
    await tracker.track("skill_dep_fail", success=True)
    for _ in range(9):
        await tracker.track("skill_dep_fail", success=False)

    # Healthy skill: 10 successes -> should NOT be flagged
    for _ in range(10):
        await tracker.track("skill_dep_ok", success=True)

    # Long-unused skill: 1 success, then push used_at back 60 days
    await tracker.track("skill_dep_stale", success=True)
    stale = tracker.get_usage("skill_dep_stale")
    assert stale is not None
    stale.used_at = datetime.now(UTC) - timedelta(days=60)

    cands = tracker.deprecate_candidates(unused_days=30, max_failure_rate=0.5)
    cand_ids = sorted(c.skill_id for c in cands)
    assert cand_ids == ["skill_dep_fail", "skill_dep_stale"]

    # min_calls=2 protects brand-new skills from being deprecated on
    # their first failure.
    await tracker.track("skill_dep_new", success=False)
    cands2 = tracker.deprecate_candidates(
        unused_days=30, max_failure_rate=0.5, min_calls=2
    )
    cand_ids2 = sorted(c.skill_id for c in cands2)
    assert "skill_dep_new" not in cand_ids2

    # stricter threshold (max_failure_rate=0.2) — skill_dep_fail still
    # qualifies (90% fail), and a 33%-failing skill also qualifies.
    await tracker.track("skill_dep_25pct", success=False)
    await tracker.track("skill_dep_25pct", success=False)
    await tracker.track("skill_dep_25pct", success=True)
    await tracker.track("skill_dep_25pct", success=True)
    await tracker.track("skill_dep_25pct", success=True)
    await tracker.track("skill_dep_25pct", success=True)
    # 4 success / 2 failure out of 6 = 66.7% success (33.3% failure)
    cands3 = tracker.deprecate_candidates(max_failure_rate=0.2)
    cand_ids3 = sorted(c.skill_id for c in cands3)
    assert "skill_dep_fail" in cand_ids3  # 90% fail
    assert "skill_dep_25pct" in cand_ids3  # 33.3% fail > 20%

    # input validation
    with pytest.raises(ValueError):
        tracker.deprecate_candidates(unused_days=-1)
    with pytest.raises(ValueError):
        tracker.deprecate_candidates(max_failure_rate=1.5)


# ---------------------------------------------------------------------------
# 5. format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_format():
    """format() renders a single-line, human-readable summary."""
    tracker = SkillUsageTracker()
    # Single track with context_hash so the latest is visible.
    await tracker.track("skill_fmt", success=True, context_hash="h-1")
    u = tracker.get_usage("skill_fmt")
    assert u is not None

    s = tracker.format(u)
    # Required substrings per the design contract:
    assert s.startswith("SkillUsage(")
    assert "skill_id=skill_fmt" in s
    assert "success=1" in s
    assert "failure=0" in s
    assert "total=1" in s
    assert "success_rate=100.00%" in s
    assert "context_hash=h-1" in s
    assert s.endswith(")")

    # A failure is added (without context_hash, so the latest wins == None).
    await tracker.track("skill_fmt", success=False)
    u2 = tracker.get_usage("skill_fmt")
    assert u2 is not None
    assert u2.success_count == 1
    assert u2.failure_count == 1
    s2 = tracker.format(u2)
    assert "success=1" in s2
    assert "failure=1" in s2
    assert "total=2" in s2
    assert "success_rate=50.00%" in s2
    assert "context_hash=None" in s2  # latest track had no hash

    # Calling format on a perfect-success aggregate.
    await tracker.track("skill_fmt_perfect", success=True)
    u3 = tracker.get_usage("skill_fmt_perfect")
    s3 = tracker.format(u3)
    assert "skill_id=skill_fmt_perfect" in s3
    assert "success_rate=100.00%" in s3

    # Calling format with no track() yet is the caller's responsibility;
    # we do not exercise that path here (u would be None).


# ---------------------------------------------------------------------------
# Evidence-grade case: 5 skills x 100 task = 500 calls (C006 evidence)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_500_calls_all_captured():
    """C006 evidence checklist: 5 skills x 100 task = 500 calls captured.

    Verifies:
      - Every call (no silent track): audit_log has exactly 500 rows.
      - Per-skill aggregates sum to 500 across all skills.
      - Per-skill success_count + failure_count == 100.
      - get_calls() returns the full history for each skill.
    """
    tracker = SkillUsageTracker()
    skill_ids = [f"skill_{i}" for i in range(5)]
    for sid in skill_ids:
        for i in range(100):
            # 80% success, 20% failure (deterministic: every 5th call fails)
            await tracker.track(sid, success=(i % 5 != 0))

    # 1. No silent track: 500 audit rows.
    assert len(tracker.audit_log) == 500

    # 2. Aggregates sum to 500.
    total_success = sum(u.success_count for u in tracker.aggregates.values())
    total_failure = sum(u.failure_count for u in tracker.aggregates.values())
    assert total_success + total_failure == 500
    assert total_success == 400  # 5 skills x 80 success each
    assert total_failure == 100  # 5 skills x 20 failure each

    # 3. Each skill has exactly 100 calls.
    for sid in skill_ids:
        u = tracker.get_usage(sid)
        assert u is not None
        assert u.total_calls() == 100
        # And success_rate() agrees with success_rate() helper.
        assert u.success_rate() == pytest.approx(0.8)
        assert tracker.success_rate(sid) == pytest.approx(0.8)

    # 4. get_calls(skill_id) returns 100 rows for each skill.
    for sid in skill_ids:
        rows = tracker.get_calls(sid)
        assert len(rows) == 100
        # Per-row types are SkillUsageAudit.
        assert all(isinstance(r, SkillUsageAudit) for r in rows)
        assert all(r.skill_id == sid for r in rows)

    # 5. deprecate_candidates returns empty (all healthy 80%).
    assert tracker.deprecate_candidates() == []
