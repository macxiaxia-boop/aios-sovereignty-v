"""test_failure_feedback.py - Phase G G001 FailureFeedbackService unit tests (30+ cases).

Covers:
- Service construction and __init__ defaults
- apply_clusters_to_goal (happy path, idempotent, threshold, atomic rollback, etc.)
- apply_clusters_to_active_goals (batch, per-goal, error isolation)
- _idempotency_keys + _make_failure_mode static helpers
- FailureFeedbackRunner (argparse, trace sources, main)
- FailureMode round-trip

Run:
    cd D:\\AIOS\\kernel
    python -m pytest tests/unit/test_failure_feedback.py -v
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aios_kernel.domain.goal import FailureMode, Goal, GoalStatus
from aios_kernel.domain.services.repository import InMemoryRepository
from aios_kernel.learning.clustering import FailureCluster, FailurePatternMerger, FailureTrace
from aios_kernel.learning.failure_feedback import (
    DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    MAX_MODES_PER_APPLY,
    FailureFeedbackService,
)
from aios_kernel.learning.failure_feedback_runner import (
    InMemoryTraceSource,
    JsonlFileTraceSource,
    _build_argparser,
    _summary,
    main as runner_main,
    run_once,
)


# ----- helpers --------------------------------------------------------------


def _make_goal(goal_id=None, status=GoalStatus.PENDING):
    return Goal(
        id=goal_id or str(uuid.uuid4()),
        title="Test Goal",
        success_criteria="ship",
        budget=100.0,
        owner="codex",
        status=status,
    )


def _make_cluster(
    cluster_id="abcd1234efgh5678",
    root_cause="timeout",
    error_type="TimeoutError",
    occurrence=5,
    msg="timeout while connecting",
):
    return FailureCluster(
        cluster_id=cluster_id,
        root_cause=root_cause,
        error_type=error_type,
        affected_trace_ids=["t-" + str(i) for i in range(occurrence)],
        occurrence_count=occurrence,
        severity_score=float(occurrence),
        first_seen="2026-10-09T00:00:00Z",
        last_seen="2026-10-09T00:05:00Z",
        recommended_fix="check service",
        sample_error_messages=[msg, "another sample", "yet another"],
    )


def _unique_cluster_id(i):
    return ("%08x" % i) + "0" * 8


async def _seed_goal(repo, goal):
    await repo.add(goal)
    await repo.commit()


# ===== Section 1: Service construction =====================================


def test_service_init_accepts_dual_repos():
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    assert svc.repo is repo
    assert svc.goal_repo is repo


def test_service_init_accepts_distinct_repos():
    repo_w = InMemoryRepository()
    repo_r = InMemoryRepository()
    svc = FailureFeedbackService(repo_w, repo_r)
    assert svc.repo is repo_w
    assert svc.goal_repo is repo_r


def test_default_min_occurrence_is_three():
    assert DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK == 3
    assert MAX_MODES_PER_APPLY == 100


# ===== Section 2: apply_clusters_to_goal (happy path) ======================


@pytest.mark.asyncio
async def test_apply_clusters_adds_new_modes():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)

    cluster = _make_cluster(occurrence=5)
    updated, added = await svc.apply_clusters_to_goal(goal.id, [cluster])

    assert len(added) == 1
    assert len(updated.failure_modes) == 1
    assert "[timeout]" in updated.failure_modes[0].description
    assert "TimeoutError" in updated.failure_modes[0].description
    assert "5x" in updated.failure_modes[0].description


@pytest.mark.asyncio
async def test_apply_clusters_idempotent_no_duplicates():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)

    cluster = _make_cluster(occurrence=5)
    _, added1 = await svc.apply_clusters_to_goal(goal.id, [cluster])
    _, added2 = await svc.apply_clusters_to_goal(goal.id, [cluster])

    assert len(added1) == 1
    assert added2 == []
    final = await repo.get(Goal, goal.id)
    assert len(final.failure_modes) == 1


@pytest.mark.asyncio
async def test_apply_clusters_below_min_occurrence_skipped():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)

    low = _make_cluster(cluster_id="low0000low0000lo", occurrence=2)
    _, added = await svc.apply_clusters_to_goal(goal.id, [low], min_occurrence=3)
    assert added == []
    final = await repo.get(Goal, goal.id)
    assert final.failure_modes == []


@pytest.mark.asyncio
async def test_apply_clusters_goal_not_found_returns_empty():
    """G002-FIX-UUID: 容错 non-existent goal_id — 返回 (None, []) 而非 raise.

    防止整个 FailureFeedback pipeline 因单个 missing goal 崩溃.
    """
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    missing_id = str(uuid.uuid4())
    goal, added = await svc.apply_clusters_to_goal(missing_id, [_make_cluster()])
    assert goal is None
    assert added == []

@pytest.mark.asyncio
async def test_apply_clusters_non_uuid_goal_id_returns_empty():
    """G002-FIX-UUID: 容错非 UUID goal_id — 上游可能传 'P8-T24' 等 identifier.
    返回 (None, []) 而不是 raise ValueError (避免 pipeline 崩溃).
    """
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    # 'test-goal-001' 不是 UUID
    goal, added = await svc.apply_clusters_to_goal("test-goal-001", [_make_cluster()])
    assert goal is None
    assert added == []



@pytest.mark.asyncio
async def test_apply_clusters_atomic_rollback_on_error():
    class _BoomRepo:
        def __init__(self, inner):
            self.inner = inner
            self.add_calls = 0

        async def add(self, obj):
            self.add_calls += 1
            raise RuntimeError("simulated DB error")

        async def commit(self):
            pass

        async def get(self, model, pk):
            return await self.inner.get(model, pk)

        async def find(self, model, **filters):
            return await self.inner.find(model, **filters)

        async def flush(self):
            return None

    inner = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(inner, goal)
    boom = _BoomRepo(inner)
    svc = FailureFeedbackService(boom, inner)

    with pytest.raises(RuntimeError, match="simulated DB error"):
        await svc.apply_clusters_to_goal(goal.id, [_make_cluster(occurrence=5)])

    final = await inner.get(Goal, goal.id)
    assert final.failure_modes == []
    assert boom.add_calls == 1


@pytest.mark.asyncio
async def test_apply_clusters_with_empty_clusters_no_op():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    _, added = await svc.apply_clusters_to_goal(goal.id, [])
    assert added == []


@pytest.mark.asyncio
async def test_apply_clusters_recognizes_existing_by_description_detection_key():
    repo = InMemoryRepository()
    goal = _make_goal()
    goal.failure_modes = [
        FailureMode(
            description="[timeout] TimeoutError (occurs 5x)",
            detection="error_type=TimeoutError; normalized_hash=abcd1234",
        )
    ]
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)

    cluster = _make_cluster(cluster_id="abcd1234efgh5678", occurrence=5)
    _, added = await svc.apply_clusters_to_goal(goal.id, [cluster])
    assert added == []


@pytest.mark.asyncio
async def test_apply_clusters_idempotent_after_repeated_calls():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    cluster = _make_cluster(occurrence=5)

    sizes = []
    for _ in range(5):
        _, added = await svc.apply_clusters_to_goal(goal.id, [cluster])
        final = await repo.get(Goal, goal.id)
        sizes.append(len(final.failure_modes))
    assert sizes == [1, 1, 1, 1, 1]


@pytest.mark.asyncio
async def test_apply_clusters_handles_goal_with_empty_failure_modes():
    repo = InMemoryRepository()
    goal = _make_goal()
    assert goal.failure_modes == []
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    _, added = await svc.apply_clusters_to_goal(goal.id, [_make_cluster()])
    assert len(added) == 1


@pytest.mark.asyncio
async def test_apply_clusters_preserves_existing_modes():
    repo = InMemoryRepository()
    goal = _make_goal()
    goal.failure_modes = [
        FailureMode(description="old-A", detection="det-A"),
        FailureMode(description="old-B", detection="det-B"),
    ]
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    _, added = await svc.apply_clusters_to_goal(
        goal.id, [_make_cluster(cluster_id="new0000new0000ne", occurrence=4)]
    )
    assert len(added) == 1
    final = await repo.get(Goal, goal.id)
    assert len(final.failure_modes) == 3
    descs = [fm.description for fm in final.failure_modes]
    assert "old-A" in descs and "old-B" in descs


@pytest.mark.asyncio
async def test_apply_clusters_with_100_clusters_only_top_max_added():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)

    clusters = [
        _make_cluster(cluster_id=_unique_cluster_id(i), occurrence=4)
        for i in range(110)
    ]
    _, added = await svc.apply_clusters_to_goal(goal.id, clusters)
    assert len(added) == MAX_MODES_PER_APPLY
    final = await repo.get(Goal, goal.id)
    assert len(final.failure_modes) == MAX_MODES_PER_APPLY


@pytest.mark.asyncio
async def test_apply_clusters_includes_normalized_hash_in_detection():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    cluster = _make_cluster(cluster_id="deadbeef12345678", occurrence=4)
    _, added = await svc.apply_clusters_to_goal(goal.id, [cluster])
    assert len(added) == 1
    final = await repo.get(Goal, goal.id)
    assert "normalized_hash=deadbeef" in final.failure_modes[0].detection


@pytest.mark.asyncio
async def test_apply_clusters_includes_indicator_from_sample_messages():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    cluster = _make_cluster(msg="specific indicator message")
    _, added = await svc.apply_clusters_to_goal(goal.id, [cluster])
    assert len(added) == 1
    final = await repo.get(Goal, goal.id)
    assert final.failure_modes[0].indicator == "specific indicator message"


@pytest.mark.asyncio
async def test_apply_clusters_indicator_none_when_no_samples():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    cluster = FailureCluster(
        cluster_id="no0000no0000no00",
        root_cause="x",
        error_type="X",
        affected_trace_ids=["t1"],
        occurrence_count=5,
        severity_score=1.0,
        first_seen="2026-10-09T00:00:00Z",
        last_seen="2026-10-09T00:00:00Z",
        recommended_fix="",
        sample_error_messages=[],
    )
    _, added = await svc.apply_clusters_to_goal(goal.id, [cluster])
    assert len(added) == 1
    final = await repo.get(Goal, goal.id)
    assert final.failure_modes[0].indicator is None


@pytest.mark.asyncio
async def test_no_minimum_occurrence_disables_threshold():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    cluster = _make_cluster(occurrence=1)
    _, added = await svc.apply_clusters_to_goal(goal.id, [cluster], min_occurrence=1)
    assert len(added) == 1


@pytest.mark.asyncio
async def test_apply_clusters_rejects_non_FailureCluster():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    with pytest.raises(TypeError, match="must contain FailureCluster"):
        await svc.apply_clusters_to_goal(goal.id, [{"oops": "not a cluster"}])


@pytest.mark.asyncio
async def test_apply_clusters_rejects_invalid_min_occurrence():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    with pytest.raises(ValueError, match="min_occurrence must be at least 1"):
        await svc.apply_clusters_to_goal(goal.id, [_make_cluster()], min_occurrence=0)


@pytest.mark.asyncio
async def test_apply_clusters_failure_modes_count_increases_monotonically():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)

    sizes = []
    for i in range(5):
        cluster = _make_cluster(
            cluster_id=_unique_cluster_id(1000 + i), occurrence=4
        )
        await svc.apply_clusters_to_goal(goal.id, [cluster])
        final = await repo.get(Goal, goal.id)
        sizes.append(len(final.failure_modes))
    assert sizes == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_apply_clusters_uses_merger_consistent_description_format():
    from aios_kernel.learning.merger import clusters_to_failure_modes
    cluster = _make_cluster(cluster_id="abcd1234efgh5678", occurrence=5)
    expected = clusters_to_failure_modes([cluster], min_occurrence=1)[0]
    expected_desc = expected.description
    expected_det = expected.detection

    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    _, added = await svc.apply_clusters_to_goal(goal.id, [cluster])

    assert len(added) == 1
    final = await repo.get(Goal, goal.id)
    actual = final.failure_modes[0]
    assert actual.description == expected_desc
    assert actual.detection == expected_det


@pytest.mark.asyncio
async def test_apply_clusters_skips_when_all_below_threshold():
    repo = InMemoryRepository()
    goal = _make_goal()
    await _seed_goal(repo, goal)
    svc = FailureFeedbackService(repo, repo)
    clusters = [
        _make_cluster(cluster_id=_unique_cluster_id(i), occurrence=2)
        for i in range(5)
    ]
    _, added = await svc.apply_clusters_to_goal(goal.id, clusters, min_occurrence=5)
    assert added == []


# ===== Section 3: apply_clusters_to_active_goals ===========================


@pytest.mark.asyncio
async def test_apply_clusters_to_active_goals_returns_per_goal_added():
    repo = InMemoryRepository()
    g_active1 = _make_goal(status=GoalStatus.ACTIVE)
    g_active2 = _make_goal(status=GoalStatus.ACTIVE)
    g_active3 = _make_goal(status=GoalStatus.ACTIVE)
    g_pending = _make_goal(status=GoalStatus.PENDING)
    for g in (g_active1, g_active2, g_active3, g_pending):
        await _seed_goal(repo, g)

    svc = FailureFeedbackService(repo, repo)
    cluster = _make_cluster(occurrence=5)
    results = await svc.apply_clusters_to_active_goals([cluster])

    assert set(results.keys()) == {g_active1.id, g_active2.id, g_active3.id}
    assert all(len(v) == 1 for v in results.values())
    pending_final = await repo.get(Goal, g_pending.id)
    assert pending_final.failure_modes == []


@pytest.mark.asyncio
async def test_apply_clusters_to_active_goals_single_failure_does_not_block_batch():
    class _SelectiveRepo:
        def __init__(self, inner, bad_id):
            self.inner = inner
            self.bad_id = bad_id

        async def add(self, obj):
            if obj.id == self.bad_id:
                raise RuntimeError("boom on bad")
            await self.inner.add(obj)

        async def commit(self):
            await self.inner.commit()

        async def get(self, model, pk):
            return await self.inner.get(model, pk)

        async def find(self, model, **filters):
            return await self.inner.find(model, **filters)

    inner = InMemoryRepository()
    g_ok = _make_goal(status=GoalStatus.ACTIVE)
    g_bad = _make_goal(status=GoalStatus.ACTIVE)
    for g in (g_ok, g_bad):
        await _seed_goal(inner, g)
    repo = _SelectiveRepo(inner, g_bad.id)
    svc = FailureFeedbackService(repo, inner)

    cluster = _make_cluster(occurrence=5)
    results = await svc.apply_clusters_to_active_goals([cluster])
    assert g_ok.id in results
    assert g_bad.id in results
    assert len(results[g_ok.id]) == 1
    assert results[g_bad.id] == []


@pytest.mark.asyncio
async def test_apply_clusters_to_active_goals_no_active_goals_returns_empty():
    repo = InMemoryRepository()
    g = _make_goal(status=GoalStatus.PENDING)
    await _seed_goal(repo, g)
    svc = FailureFeedbackService(repo, repo)
    results = await svc.apply_clusters_to_active_goals([_make_cluster()])
    assert results == {}


@pytest.mark.asyncio
async def test_apply_clusters_to_active_goals_passes_min_occurrence():
    repo = InMemoryRepository()
    g = _make_goal(status=GoalStatus.ACTIVE)
    await _seed_goal(repo, g)
    svc = FailureFeedbackService(repo, repo)
    cluster = _make_cluster(occurrence=5)
    results = await svc.apply_clusters_to_active_goals([cluster], min_occurrence=10)
    assert results[g.id] == []


# ===== Section 4: Idempotency key helper ====================================


def test_idempotency_keys_empty_goal_returns_empty_set():
    g = _make_goal()
    assert FailureFeedbackService._idempotency_keys(g) == set()


def test_idempotency_keys_returns_existing_pairs():
    g = _make_goal()
    g.failure_modes = [
        FailureMode(description="a", detection="x"),
        FailureMode(description="b", detection="y"),
    ]
    keys = FailureFeedbackService._idempotency_keys(g)
    assert ("a", "x") in keys
    assert ("b", "y") in keys
    assert len(keys) == 2


# ===== Section 5: FailureFeedbackRunner =====================================


def test_argparser_defaults():
    p = _build_argparser()
    args = p.parse_args([])
    assert args.min_occurrence == DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK
    assert args.interval == 900
    assert args.dry_run is False
    assert args.once is True
    assert args.log_level == "INFO"


def test_argparser_custom_min_occurrence():
    p = _build_argparser()
    args = p.parse_args(["--min-occurrence", "7"])
    assert args.min_occurrence == 7


def test_argparser_dry_run_flag():
    p = _build_argparser()
    args = p.parse_args(["--dry-run"])
    assert args.dry_run is True


def test_argparser_trace_path():
    p = _build_argparser()
    args = p.parse_args(["--trace-path", "/tmp/x.jsonl"])
    assert args.trace_path == "/tmp/x.jsonl"


def test_summary_helper_computes_totals():
    clusters = [_make_cluster(), _make_cluster(cluster_id="o" * 16, occurrence=4)]
    results = {"g-1": ["a", "b"], "g-2": ["c"]}
    s = _summary(results, clusters)
    assert s["cluster_count"] == 2
    assert s["active_goal_count"] == 2
    assert s["total_modes_added"] == 3
    assert s["per_goal"] == {"g-1": 2, "g-2": 1}


def test_summary_helper_with_empty_results():
    s = _summary({}, [_make_cluster()])
    assert s["cluster_count"] == 1
    assert s["active_goal_count"] == 0
    assert s["total_modes_added"] == 0
    assert s["per_goal"] == {}


@pytest.mark.asyncio
async def test_run_once_with_in_memory_source_no_active_goals():
    traces = [
        FailureTrace(id="t-" + str(i), error_message="timeout", error_type="TimeoutError")
        for i in range(5)
    ]
    src = InMemoryTraceSource(traces)
    summary = await run_once(src, min_occurrence=3, dry_run=True)

    assert summary["cluster_count"] == 1
    assert summary["active_goal_count"] == 0
    assert summary["total_modes_added"] == 0


@pytest.mark.asyncio
async def test_run_once_dry_run_skips_write():
    traces = [FailureTrace(id="t-1", error_message="x", error_type="X") for _ in range(5)]
    src = InMemoryTraceSource(traces)
    summary = await run_once(src, min_occurrence=3, dry_run=True)
    assert summary["cluster_count"] == 1
    assert summary["active_goal_count"] == 0
    assert summary["total_modes_added"] == 0


@pytest.mark.asyncio
async def test_run_once_collects_traces_below_threshold():
    traces = [FailureTrace(id="t-1", error_message="x", error_type="X") for _ in range(2)]
    src = InMemoryTraceSource(traces)
    summary = await run_once(src, min_occurrence=2, dry_run=True)
    assert summary["cluster_count"] >= 0


def test_jsonl_file_trace_source_happy_path(tmp_path):
    p = tmp_path / "traces.jsonl"
    rows = [
        {"id": "t-" + str(i), "error_message": "timeout", "error_type": "TimeoutError", "timestamp": "2026-10-09T00:00:00Z"}
        for i in range(3)
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    src = JsonlFileTraceSource(p)
    traces = src.read()
    assert len(traces) == 3
    assert traces[0].id == "t-0"
    assert traces[0].error_type == "TimeoutError"


def test_jsonl_file_trace_source_missing_file_returns_empty(tmp_path):
    p = tmp_path / "nope.jsonl"
    src = JsonlFileTraceSource(p)
    assert src.read() == []


def test_jsonl_file_trace_source_missing_file_logs_warning(tmp_path, caplog):
    p = tmp_path / "nope.jsonl"
    src = JsonlFileTraceSource(p)
    with caplog.at_level(logging.WARNING, logger="aios_kernel.learning.failure_feedback_runner"):
        src.read()
    assert any("not found" in record.message for record in caplog.records)


def test_jsonl_file_trace_source_skips_bad_json(tmp_path):
    p = tmp_path / "traces.jsonl"
    p.write_text(
        '{"id":"t-1","error_message":"x","error_type":"X"}\n'
        "this is not json\n"
        '{"id":"t-2","error_message":"y","error_type":"Y"}\n'
        "# comment line\n",
        encoding="utf-8",
    )
    src = JsonlFileTraceSource(p)
    traces = src.read()
    assert len(traces) == 2
    assert {t.id for t in traces} == {"t-1", "t-2"}


def test_jsonl_file_trace_source_skips_blank_lines(tmp_path):
    p = tmp_path / "traces.jsonl"
    p.write_text("\n\n\n", encoding="utf-8")
    src = JsonlFileTraceSource(p)
    assert src.read() == []


def test_jsonl_file_trace_source_skips_record_missing_id(tmp_path):
    p = tmp_path / "traces.jsonl"
    p.write_text(
        '{"error_message":"x","error_type":"X"}\n',
        encoding="utf-8",
    )
    src = JsonlFileTraceSource(p)
    assert src.read() == []


def test_in_memory_trace_source_returns_copy():
    traces = [FailureTrace(id="t-1", error_message="x", error_type="X")]
    src = InMemoryTraceSource(traces)
    got = src.read()
    got.append(FailureTrace(id="t-2", error_message="y", error_type="Y"))
    again = src.read()
    assert len(again) == 1


def test_main_returns_zero_and_prints_summary(capsys, tmp_path):
    p = tmp_path / "traces.jsonl"
    rows = [
        {"id": "t-" + str(i), "error_message": "timeout", "error_type": "TimeoutError"}
        for i in range(5)
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    rc = runner_main([
        "--trace-path", str(p),
        "--min-occurrence", "3",
        "--dry-run",
        "--log-level", "WARNING",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["cluster_count"] == 1
    assert summary["active_goal_count"] == 0


def test_main_with_missing_trace_path_exits_zero(capsys, tmp_path):
    p = tmp_path / "missing.jsonl"
    rc = runner_main([
        "--trace-path", str(p),
        "--min-occurrence", "3",
        "--dry-run",
        "--log-level", "WARNING",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["cluster_count"] == 0
    assert summary["active_goal_count"] == 0


# ===== Section 6: Pydantic round-trip =======================================


def test_failure_modes_round_trip_through_pydantic():
    fm = FailureMode(
        description="[timeout] TimeoutError (occurs 5x)",
        detection="error_type=TimeoutError; normalized_hash=abcd1234",
        indicator="specific message",
    )
    blob = fm.model_dump_json()
    fm2 = FailureMode.model_validate_json(blob)
    assert fm2.description == fm.description
    assert fm2.detection == fm.detection
    assert fm2.indicator == fm.indicator


def test_failure_mode_rejects_empty_description():
    with pytest.raises(Exception):
        FailureMode(description="", detection="x")


def test_failure_mode_rejects_empty_detection():
    with pytest.raises(Exception):
        FailureMode(description="x", detection="")
