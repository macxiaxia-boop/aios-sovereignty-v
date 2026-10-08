"""test_replay_engine.py - C005 tests."""
from __future__ import annotations
import asyncio
from unittest.mock import MagicMock


def test_replay_success():
    from aios_kernel.learning.replay_engine import ReplayEngine
    eng = ReplayEngine()
    historical = {"run_id": "r1", "outputs": {"status": "ok", "value": 42}}
    new_outputs = {"status": "ok", "value": 42}
    result = asyncio.run(eng.replay(historical, new_outputs))
    assert result.status == "success"
    assert result.diffs_from_expected == []
    assert result.historical_run_id == "r1"


def test_replay_drift():
    from aios_kernel.learning.replay_engine import ReplayEngine
    eng = ReplayEngine()
    historical = {"run_id": "r2", "outputs": {"x": 1, "y": 2}}
    new_outputs = {"x": 1, "y": 3}  # y drifted
    result = asyncio.run(eng.replay(historical, new_outputs))
    assert result.status == "drift"
    assert len(result.diffs_from_expected) == 1
    assert "y" in result.diffs_from_expected[0]


def test_replay_failure_when_outputs_empty():
    from aios_kernel.learning.replay_engine import ReplayEngine
    eng = ReplayEngine()
    historical = {"run_id": "r3", "outputs": {"x": 1}}
    new_outputs = {}
    result = asyncio.run(eng.replay(historical, new_outputs))
    assert result.status == "failure"


def test_diff_detect_added_keys():
    from aios_kernel.learning.replay_engine import ReplayEngine
    eng = ReplayEngine()
    diffs = eng.diff_detect({"a": 1}, {"a": 1, "b": 2})
    assert len(diffs) == 1
    assert "b" in diffs[0]


def test_replay_100_runs():
    from aios_kernel.learning.replay_engine import ReplayEngine
    eng = ReplayEngine()
    for i in range(100):
        historical = {"run_id": f"r{i}", "outputs": {"v": i}}
        new_outputs = {"v": i}  # all match
        result = asyncio.run(eng.replay(historical, new_outputs))
        assert result.status == "success"
    assert len(eng._results) == 100
