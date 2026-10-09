"""Unit tests for F004 deterministic failure-pattern merging."""
from __future__ import annotations

from time import perf_counter

import pytest

from aios_kernel.learning.clustering import (
    FailureCluster,
    FailurePatternMerger,
    FailureTrace,
    merge_rate,
)
from aios_kernel.learning.merger import (
    clusters_to_failure_modes,
    suggest_preserve_capabilities,
)


def trace(
    trace_id: int,
    message: str = "connection timeout",
    error_type: str = "TimeoutError",
    timestamp: str = "2026-10-08T10:00:00Z",
    context: dict | None = None,
) -> FailureTrace:
    return FailureTrace(
        id=f"trace-{trace_id}",
        error_message=message,
        error_type=error_type,
        context=context or {},
        timestamp=timestamp,
    )


def test_normalize_strips_windows_paths() -> None:
    normalized = FailurePatternMerger()._normalize(r"Cannot open C:\Users\alice\input.csv")
    assert normalized == "cannot open <path>"


def test_normalize_strips_unc_paths() -> None:
    normalized = FailurePatternMerger()._normalize(r"Cannot open \\server\share\input.csv")
    assert normalized == "cannot open <path>"


def test_normalize_strips_ips() -> None:
    assert "<ip>" in FailurePatternMerger()._normalize("connect 10.2.30.41 failed")


def test_normalize_strips_numbers() -> None:
    assert FailurePatternMerger()._normalize("retry 42 after 3.5 seconds") == (
        "retry <num> after <num> seconds"
    )


def test_normalize_strips_uuids() -> None:
    value = "request a8098bcd-28ff-463d-a4c8-5d8f61e10000 failed"
    assert FailurePatternMerger()._normalize(value) == "request <uuid> failed"


def test_normalize_strips_timestamps() -> None:
    value = "event 2026-10-08T23:22:33.123Z failed"
    assert FailurePatternMerger()._normalize(value) == "event <ts> failed"


def test_same_message_same_hash() -> None:
    merger = FailurePatternMerger()
    assert merger._hash(merger._normalize("Timeout at 10:00")) == merger._hash(
        merger._normalize("timeout AT 10:00")
    )


def test_different_message_different_hash() -> None:
    merger = FailurePatternMerger()
    assert merger._hash(merger._normalize("timeout")) != merger._hash(
        merger._normalize("permission denied")
    )


def test_empty_input_returns_empty() -> None:
    assert FailurePatternMerger().merge([]) == []


def test_single_failure_returns_one_cluster() -> None:
    clusters = FailurePatternMerger().merge([trace(1)])
    assert len(clusters) == 1
    assert clusters[0].affected_trace_ids == ["trace-1"]


def test_50_similar_failures_cluster_to_leq_10() -> None:
    failures = [trace(i, f"timeout after {i} seconds") for i in range(50)]
    clusters = FailurePatternMerger().merge(failures)
    assert len(clusters) == 1
    assert clusters[0].occurrence_count == 50


def test_50_dissimilar_failures_no_merge() -> None:
    failures = [trace(i, f"failure {chr(97 + i)} {chr(97 + i // 26)}") for i in range(50)]
    clusters = FailurePatternMerger().merge(failures)
    assert len(clusters) == 50
    assert merge_rate(50, clusters) == 0.0


def test_min_samples_keeps_singleton_but_marks_low_severity() -> None:
    clusters = FailurePatternMerger(min_samples=3).merge([trace(1), trace(2, "other")])
    assert len(clusters) == 2
    assert min(cluster.occurrence_count for cluster in clusters) == 1


def test_severity_increases_with_occurrence() -> None:
    merger = FailurePatternMerger()
    assert merger._severity(3, 1.0) > merger._severity(2, 1.0)


def test_severity_capped_at_10() -> None:
    assert FailurePatternMerger()._severity(100, 2.0) == 10.0


def test_root_cause_permission_error() -> None:
    assert FailurePatternMerger()._root_cause("PermissionError", "denied") == "permission_denied"


def test_root_cause_file_not_found() -> None:
    assert FailurePatternMerger()._root_cause("FileNotFoundError", "missing") == "file_missing"


def test_root_cause_timeout() -> None:
    assert FailurePatternMerger()._root_cause("TimeoutError", "slow") == "timeout"


def test_root_cause_connection_error() -> None:
    assert FailurePatternMerger()._root_cause("ConnectionError", "failed") == "network_unavailable"


def test_root_cause_validation_error() -> None:
    assert FailurePatternMerger()._root_cause("ValidationError", "bad") == "input_invalid"


def test_root_cause_unknown_fallback() -> None:
    assert FailurePatternMerger()._root_cause("CustomError", "bad") == "unknown:CustomError"


def test_clusters_sorted_by_severity_desc() -> None:
    failures = [
        trace(1, "rare"),
        *[trace(i, "common") for i in range(2, 6)],
    ]
    clusters = FailurePatternMerger().merge(failures)
    assert clusters[0].occurrence_count == 4
    assert clusters[1].occurrence_count == 1


def test_cluster_tracks_first_and_last_seen() -> None:
    failures = [
        trace(1, timestamp="2026-10-08T12:00:02Z"),
        trace(2, timestamp="2026-10-08T12:00:00Z"),
    ]
    cluster = FailurePatternMerger().merge(failures)[0]
    assert cluster.first_seen == "2026-10-08T12:00:00Z"
    assert cluster.last_seen == "2026-10-08T12:00:02Z"


def test_cluster_samples_at_most_five_messages() -> None:
    cluster = FailurePatternMerger().merge([trace(i) for i in range(10)])[0]
    assert len(cluster.sample_error_messages) == 5


def test_context_impact_affects_severity() -> None:
    low = FailurePatternMerger().merge([trace(1, context={"impact": 0.5})])[0]
    high = FailurePatternMerger().merge([trace(2, context={"impact": 2.0})])[0]
    assert low.severity_score < high.severity_score


def test_invalid_eps_rejected() -> None:
    with pytest.raises(ValueError):
        FailurePatternMerger(eps=0)


def test_invalid_min_samples_rejected() -> None:
    with pytest.raises(ValueError):
        FailurePatternMerger(min_samples=0)


def test_non_failure_trace_rejected() -> None:
    with pytest.raises(TypeError):
        FailurePatternMerger().merge([{"error_message": "bad"}])  # type: ignore[list-item]


def test_clusters_to_failure_modes_min_occurrence() -> None:
    failures = [trace(i) for i in range(4)]
    clusters = FailurePatternMerger().merge(failures)
    modes = clusters_to_failure_modes(clusters)
    assert len(modes) == 1
    assert modes[0].detection.startswith("error_type=TimeoutError")


def test_clusters_to_failure_modes_filters_singletons() -> None:
    clusters = FailurePatternMerger().merge([trace(1), trace(2, "other")])
    assert clusters_to_failure_modes(clusters) == []


def test_suggest_preserve_capabilities_returns_list() -> None:
    assert suggest_preserve_capabilities([]) == [
        "verifier/deterministic.py (don't touch)",
        "v2 consumer main loop (don't refactor)",
        "AGENTS.md SSOT",
    ]


def test_merge_rate_50_to_5_is_90pct() -> None:
    empty = [FailureCluster("", "", "", [], 0, 0, "", "", "", []) for _ in range(5)]
    assert merge_rate(50, empty) == pytest.approx(0.90)


def test_merge_rate_50_to_50_is_0pct() -> None:
    empty = [FailureCluster("", "", "", [], 0, 0, "", "", "", []) for _ in range(50)]
    assert merge_rate(50, empty) == 0.0


def test_merge_rate_empty_is_0() -> None:
    assert merge_rate(0, []) == 0.0


def test_1000_failures_processed_under_1_second() -> None:
    failures = [trace(i, f"timeout after {i} seconds") for i in range(1000)]
    started = perf_counter()
    clusters = FailurePatternMerger().merge(failures)
    elapsed = perf_counter() - started
    assert len(clusters) == 1
    assert elapsed < 1.0

