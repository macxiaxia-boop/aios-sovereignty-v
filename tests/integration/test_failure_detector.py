"""test_failure_detector.py - C003 tests."""
from __future__ import annotations
from datetime import UTC, datetime
from unittest.mock import MagicMock


def test_detect_empty():
    from aios_kernel.learning.failure_detector import FailureDetector
    det = FailureDetector()
    result = det.detect([])
    assert result == []


def test_detect_clusters_similar_failures():
    from aios_kernel.learning.failure_detector import FailureDetector
    det = FailureDetector()
    # 5 failures with same error → 1 cluster
    traces = []
    for i in range(5):
        t = MagicMock()
        t.id = f"f_{i}"
        t.event_type = "task.fail"
        t.timestamp = datetime.now(UTC)
        t.payload = {"error": "TypeError: x is None"}
        traces.append(t)
    clusters = det.detect(traces)
    assert len(clusters) == 1
    assert clusters[0].occurrence_count == 5
    assert "TypeError" in clusters[0].root_cause


def test_detect_clusters_separate_failures():
    from aios_kernel.learning.failure_detector import FailureDetector
    det = FailureDetector()
    traces = []
    # 2 TypeError + 3 ValueError → 2 clusters
    for i in range(2):
        t = MagicMock()
        t.id = f"t_{i}"
        t.event_type = "task.fail"
        t.timestamp = datetime.now(UTC)
        t.payload = {"error": "TypeError"}
        traces.append(t)
    for i in range(3):
        t = MagicMock()
        t.id = f"v_{i}"
        t.event_type = "verify.fail"
        t.timestamp = datetime.now(UTC)
        t.payload = {"error": "ValueError"}
        traces.append(t)
    clusters = det.detect(traces)
    assert len(clusters) == 2


def test_prioritize_by_severity():
    from aios_kernel.learning.failure_detector import FailureDetector
    det = FailureDetector()
    traces = []
    # 1 critical, 5 low
    for i in range(12):
        t = MagicMock()
        t.id = f"c_{i}"
        t.event_type = "task.fail"
        t.timestamp = datetime.now(UTC)
        t.payload = {"error": "CriticalError"}
        traces.append(t)
    for i in range(2):
        t = MagicMock()
        t.id = f"l_{i}"
        t.event_type = "task.fail"
        t.timestamp = datetime.now(UTC)
        t.payload = {"error": "LowError"}
        traces.append(t)
    clusters = det.detect(traces)
    assert clusters[0].severity == "critical"
    assert clusters[0].occurrence_count == 12
