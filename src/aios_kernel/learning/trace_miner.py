"""trace_miner.py - C002 Trace Mining layer."""
from __future__ import annotations
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Iterable, Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow
from aios_kernel.persistence.models import TraceORM


class TracePattern(Envelope):
    pattern_type: str  # "success" | "failure" | "anomaly"
    description: str
    frequency: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    example_trace_ids: list[str] = Field(default_factory=list)


class TraceMiner:
    """Mines TraceORM rows for success/failure patterns."""

    def __init__(self):
        self._patterns: list[TracePattern] = []

    async def mine(self, traces: Iterable[TraceORM], time_range: tuple = None) -> list[TracePattern]:
        """Mine traces within optional (start, end) time range."""
        patterns = []
        events_by_type: dict[str, list[TraceORM]] = defaultdict(list)
        for t in traces:
            if t.event_type in ("task.complete", "task.fail", "verify.pass", "verify.fail"):
                events_by_type[t.event_type].append(t)

        # Build patterns
        for event_type, ts in events_by_type.items():
            pattern_type = "success" if event_type.endswith(".complete") or "pass" in event_type else "failure"
            desc = f"{event_type} occurred {len(ts)} times"
            first = min(t.timestamp for t in ts if t.timestamp) if any(t.timestamp for t in ts) else None
            last = max(t.timestamp for t in ts if t.timestamp) if any(t.timestamp for t in ts) else None
            pat = TracePattern(
                id=str(uuid.uuid4()),
                pattern_type=pattern_type,
                description=desc,
                frequency=len(ts),
                first_seen=first,
                last_seen=last,
                example_trace_ids=[str(t.id) for t in ts[:5]],
            )
            patterns.append(pat)
        return patterns


__all__ = ["TracePattern", "TraceMiner"]
