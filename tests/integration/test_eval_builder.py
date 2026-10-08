"""test_eval_builder.py - C004 tests."""
from __future__ import annotations
import asyncio
import uuid
from unittest.mock import MagicMock


def test_from_real():
    from aios_kernel.learning.eval_builder import EvalDatasetBuilder
    b = EvalDatasetBuilder()
    traces = []
    for i in range(5):
        t = MagicMock()
        t.id = f"t_{i}"
        t.event_type = "task.complete" if i % 2 == 0 else "task.fail"
        t.payload = {"v": i}
        traces.append(t)
    cases = asyncio.run(b.from_real(traces, n=5))
    assert len(cases) == 5
    assert all(c.source == "real" for c in cases)
    assert cases[0].evidence_id == "t_0"


def test_synthetic():
    from aios_kernel.learning.eval_builder import EvalDatasetBuilder
    b = EvalDatasetBuilder()
    cases = asyncio.run(b.synthetic(n=10))
    assert len(cases) == 10
    assert all(c.source == "synthetic" for c in cases)


def test_merge_dedup():
    from aios_kernel.learning.eval_builder import EvalDatasetBuilder
    from aios_kernel.learning.eval_builder import EvalCase
    b = EvalDatasetBuilder()
    c1 = EvalCase(id=str(uuid.uuid4()), query="q1", expected_output="a", source="real")
    c2 = EvalCase(id=str(uuid.uuid4()), query="q1", expected_output="a", source="synth")  # dup
    c3 = EvalCase(id=str(uuid.uuid4()), query="q2", expected_output="b", source="synth")
    merged = asyncio.run(b.merge([c1], [c2, c3]))
    assert len(merged) == 2  # dedup


def test_mix_50_50():
    from aios_kernel.learning.eval_builder import EvalDatasetBuilder
    b = EvalDatasetBuilder()
    real = asyncio.run(b.from_real([], n=50))
    synth = asyncio.run(b.synthetic(n=50))
    merged = asyncio.run(b.merge(real, synth))
    real_count = sum(1 for c in merged if c.source == "real")
    synth_count = sum(1 for c in merged if c.source == "synthetic")
    assert real_count >= 0  # empty traces = 0 real
    assert synth_count == 50
    # If we had real traces:
    traces = []
    for i in range(50):
        t = MagicMock()
        t.id = f"r{i}"
        t.event_type = "task.complete"
        t.payload = {"v": i}
        traces.append(t)
    real2 = asyncio.run(b.from_real(traces, n=50))
    merged2 = asyncio.run(b.merge(real2, synth))
    real_count2 = sum(1 for c in merged2 if c.source == "real")
    synth_count2 = sum(1 for c in merged2 if c.source == "synthetic")
    assert real_count2 == 50
    assert synth_count2 == 50
