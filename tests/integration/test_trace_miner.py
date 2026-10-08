"""test_trace_miner.py - C002 tests."""
from __future__ import annotations
from datetime import UTC, datetime
from unittest.mock import MagicMock


def test_mine_empty():
    from aios_kernel.learning.trace_miner import TraceMiner
    miner = TraceMiner()
    import asyncio
    result = asyncio.run(miner.mine([]))
    assert result == []


def test_mine_extracts_success_and_failure():
    from aios_kernel.learning.trace_miner import TraceMiner
    miner = TraceMiner()
    # Mock 5 success + 3 failure traces
    traces = []
    for i in range(5):
        t = MagicMock()
        t.id = f"trace_success_{i}"
        t.event_type = "task.complete"
        t.timestamp = datetime.now(UTC)
        t.payload = {}
        traces.append(t)
    for i in range(3):
        t = MagicMock()
        t.id = f"trace_fail_{i}"
        t.event_type = "task.fail"
        t.timestamp = datetime.now(UTC)
        t.payload = {"error": "x"}
        traces.append(t)
    import asyncio
    patterns = asyncio.run(miner.mine(traces))
    assert len(patterns) >= 2  # at least one success + one failure
    success_pattern = next(p for p in patterns if p.pattern_type == "success")
    assert success_pattern.frequency == 5
    fail_pattern = next(p for p in patterns if p.pattern_type == "failure")
    assert fail_pattern.frequency == 3


def test_pattern_includes_example_ids():
    from aios_kernel.learning.trace_miner import TraceMiner
    miner = TraceMiner()
    traces = []
    for i in range(3):
        t = MagicMock()
        t.id = f"t_{i}"
        t.event_type = "task.complete"
        t.timestamp = datetime.now(UTC)
        t.payload = {}
        traces.append(t)
    import asyncio
    pats = asyncio.run(miner.mine(traces))
    assert pats[0].example_trace_ids == ["t_0", "t_1", "t_2"]
