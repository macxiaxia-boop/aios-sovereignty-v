"""Integration acceptance tests for F004 failure clustering."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aios_kernel.domain.goal import Goal
from aios_kernel.learning.clustering import (
    FailurePatternMerger,
    FailureTrace,
    merge_rate,
)
from aios_kernel.learning.merger import clusters_to_failure_modes


def generate_realistic_failures(count: int = 50) -> list[FailureTrace]:
    """Generate realistic operational errors with volatile IDs, paths, IPs and times."""
    templates = (
        (r"FileNotFoundError", r"missing report C:\reports\daily_{index}.csv", {}),
        ("TimeoutError", "upstream timed out after {index} seconds", {"impact": 2.0}),
        ("ConnectionError", "connection to 10.20.{shard}.41 refused", {}),
        ("PermissionError", r"permission denied for D:\private\case_{index}.db", {}),
        (
            "ValidationError",
            "invalid input payload {uuid} for tenant {index}",
            {"impact": 1.5},
        ),
    )
    base = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    failures: list[FailureTrace] = []
    for index in range(count):
        error_type, template, context = templates[index % len(templates)]
        message = template.format(
            index=index + 1,
            shard=(index % len(templates)) + 1,
            uuid=f"a8098bcd-28ff-463d-a4c8-{index + 1:012d}",
        )
        failures.append(
            FailureTrace(
                id=f"real-failure-{index + 1:03d}",
                error_message=message,
                error_type=error_type,
                context=context,
                timestamp=(base + timedelta(seconds=index)).isoformat(),
            )
        )
    return failures


def test_50_real_failures_merged_to_clusters() -> None:
    failures = generate_realistic_failures(50)
    clusters = FailurePatternMerger().merge(failures)
    rate = merge_rate(50, clusters)
    assert len(clusters) <= 10
    assert rate >= 0.70, f"merge rate {rate:.2%} < 70%"
    assert sum(cluster.occurrence_count for cluster in clusters) == 50


def test_clusters_can_be_loaded_into_goal_contract() -> None:
    failures = generate_realistic_failures(20)
    clusters = FailurePatternMerger().merge(failures)
    modes = clusters_to_failure_modes(clusters)
    goal = Goal(
        title="test",
        success_criteria="x",
        budget=0,
        owner="codex",
        failure_modes=modes,
    )
    assert len(goal.failure_modes) > 0
    assert goal.failure_modes[0].description
    assert goal.failure_modes[0].detection
