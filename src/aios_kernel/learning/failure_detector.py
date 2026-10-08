"""failure_detector.py - C003 Failure Pattern Detector."""
from __future__ import annotations
import hashlib
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Iterable

from pydantic import Field

from aios_kernel.domain.envelope import Envelope
from aios_kernel.persistence.models import TraceORM


class FailureCluster(Envelope):
    root_cause: str
    affected_traces: list[str] = Field(default_factory=list)
    occurrence_count: int = 0
    severity: str = "medium"  # "low" | "medium" | "high" | "critical"
    recommended_fix: str = ""


class FailureDetector:
    """Detect and cluster failure patterns from traces."""

    def __init__(self):
        self._clusters: list[FailureCluster] = []

    def _error_hash(self, payload: dict) -> str:
        """Hash error message for clustering (deterministic)."""
        msg = str(payload.get("error", payload.get("message", "")))
        return hashlib.sha256(msg.encode("utf-8")).hexdigest()[:8]

    def detect(self, traces: Iterable[TraceORM]) -> list[FailureCluster]:
        """Group failure traces by error hash."""
        groups: dict[str, list[TraceORM]] = defaultdict(list)
        for t in traces:
            if t.event_type in ("task.fail", "verify.fail"):
                payload = t.payload if isinstance(t.payload, dict) else {}
                key = self._error_hash(payload)
                groups[key].append(t)

        clusters = []
        for key, ts in groups.items():
            # root_cause from first failure
            first = ts[0]
            payload = first.payload if isinstance(first.payload, dict) else {}
            error_msg = payload.get("error", payload.get("message", "unknown"))
            severity = "critical" if len(ts) > 10 else "high" if len(ts) > 5 else "medium" if len(ts) > 1 else "low"
            cluster = FailureCluster(
                id=str(uuid.uuid4()),
                root_cause=error_msg[:200],
                affected_traces=[str(t.id) for t in ts],
                occurrence_count=len(ts),
                severity=severity,
                recommended_fix=f"Investigate pattern {key}; check {error_msg[:50]}",
            )
            clusters.append(cluster)
        # Sort by severity desc, then occurrence desc
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        clusters.sort(key=lambda c: (severity_order.get(c.severity, 0), c.occurrence_count), reverse=True)
        return clusters


__all__ = ["FailureCluster", "FailureDetector"]
